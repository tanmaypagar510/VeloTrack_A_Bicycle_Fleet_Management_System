import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('rag-pipeline')

IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist(dt_str):
    """Convert a UTC ISO string to IST formatted string"""
    if not dt_str or dt_str == 'N/A':
        return dt_str
    try:
        dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime('%d/%m/%Y, %I:%M:%S %p IST')
    except Exception:
        return str(dt_str)

SYSTEM_PROMPT = """You are VeloTrack's Predictive Maintenance Assistant. You help bicycle fleet staff
identify bikes that need servicing, understand maintenance patterns, and make informed decisions.

You must ONLY use the provided context (bike history records) to answer questions.
If the context doesn't contain enough information, say so clearly.
Always reference specific data points (dates, bike IDs, issue descriptions) from the context.
Be concise and actionable in your recommendations."""


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for maintenance assistant"""

    def __init__(self, vector_store, llm_client):
        self.vector_store = vector_store
        self.llm_client = llm_client

    def ask(self, question, bike_id=None):
        """Process a question through the RAG pipeline"""
        # Step 1: Enhance query with bike_id if provided
        search_query = question
        if bike_id:
            search_query = f"bicycle {bike_id} {question}"

        # Step 2: Retrieve relevant documents from vector store
        retrieved_docs = self.vector_store.search(search_query, top_k=10)

        # Step 3: Filter by bike_id if specified — only show records for that bike
        if bike_id:
            filtered_docs = [
                doc for doc in retrieved_docs
                if doc.get('metadata', {}).get('bicycle_id') == bike_id
                or f"Bike #{bike_id}" in doc.get('document', '')
            ]
            retrieved_docs = filtered_docs

        # Step 4: Build context from retrieved documents
        context_parts = []
        context_records = []
        for doc in retrieved_docs[:5]:
            context_parts.append(doc['document'])
            context_records.append({
                'text': doc['document'][:200],
                'metadata': doc.get('metadata', {})
            })

        if not context_parts:
            if bike_id:
                no_data_msg = (
                    f"No maintenance or rental history found for Bike #{bike_id}. "
                    f"This bike has not been rented or serviced yet. "
                    f"It does not need maintenance at this time based on available records."
                )
                return {
                    'answer': no_data_msg,
                    'context_used': [],
                    'question': question,
                    'bike_id': bike_id
                }
            context_text = "No relevant history found."
        else:
            context_text = "\n\n".join(context_parts)

        # Step 5: Build prompt
        prompt = f"""Based on the following bicycle fleet maintenance and rental records:

--- CONTEXT ---
{context_text}
--- END CONTEXT ---

Staff Question: {question}
{"(Specifically about bicycle ID: " + str(bike_id) + ")" if bike_id else ""}

Please provide a helpful, data-grounded response:"""

        # Step 6: Generate response using LLM
        response = self.llm_client.generate(prompt, system_prompt=SYSTEM_PROMPT)

        return {
            'answer': response,
            'context_used': context_records,
            'question': question,
            'bike_id': bike_id
        }

    def index_bike_history(self, bicycle_id, maintenance_logs, rentals):
        """Index a bike's history into the vector store"""
        documents = []
        metadata_list = []

        for log in maintenance_logs:
            doc = (
                f"Bike #{bicycle_id} - Maintenance on {_to_ist(log.get('service_date', 'unknown date'))}: "
                f"Problem: {log.get('problem_description', 'N/A')}. "
                f"Work done: {log.get('work_done', 'N/A')}. "
                f"Technician: {log.get('technician', 'N/A')}. "
                f"Cost: ₹{log.get('cost', 0)}"
            )
            documents.append(doc)
            metadata_list.append({'type': 'maintenance', 'bicycle_id': bicycle_id, 'log_id': log.get('id')})

        for rental in rentals:
            anomaly_tag = " [ANOMALOUS - unusually short]" if rental.get('is_anomalous') else ""
            return_time = rental.get('return_time')
            doc = (
                f"Bike #{bicycle_id} - Rental{anomaly_tag}: "
                f"Checked out: {_to_ist(rental.get('checkout_time', 'N/A'))}, "
                f"Returned: {_to_ist(return_time) if return_time else 'not yet returned'}. "
                f"Duration: {rental.get('duration_hours', 'N/A')} hours. "
                f"Renter: {rental.get('renter_name', 'N/A')}"
            )
            documents.append(doc)
            metadata_list.append({'type': 'rental', 'bicycle_id': bicycle_id, 'rental_id': rental.get('id')})

        if documents:
            self.vector_store.add_documents(documents, metadata_list)
            self.vector_store.save()
            logger.info(f"Indexed {len(documents)} records for bike #{bicycle_id}")

