import logging

logger = logging.getLogger('rag-pipeline')

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
        retrieved_docs = self.vector_store.search(search_query, top_k=5)

        # Step 3: Build context from retrieved documents
        context_parts = []
        context_records = []
        for doc in retrieved_docs:
            context_parts.append(doc['document'])
            context_records.append({
                'text': doc['document'][:200],
                'metadata': doc.get('metadata', {})
            })

        context_text = "\n\n".join(context_parts) if context_parts else "No relevant history found."

        # Step 4: Build prompt
        prompt = f"""Based on the following bicycle fleet maintenance and rental records:

--- CONTEXT ---
{context_text}
--- END CONTEXT ---

Staff Question: {question}
{"(Specifically about bicycle ID: " + str(bike_id) + ")" if bike_id else ""}

Please provide a helpful, data-grounded response:"""

        # Step 5: Generate response using LLM
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
                f"Bike #{bicycle_id} - Maintenance on {log.get('service_date', 'unknown date')}: "
                f"Problem: {log.get('problem_description', 'N/A')}. "
                f"Work done: {log.get('work_done', 'N/A')}. "
                f"Technician: {log.get('technician', 'N/A')}. "
                f"Cost: ${log.get('cost', 0)}"
            )
            documents.append(doc)
            metadata_list.append({'type': 'maintenance', 'bicycle_id': bicycle_id, 'log_id': log.get('id')})

        for rental in rentals:
            anomaly_tag = " [ANOMALOUS - unusually short]" if rental.get('is_anomalous') else ""
            doc = (
                f"Bike #{bicycle_id} - Rental{anomaly_tag}: "
                f"Checked out: {rental.get('checkout_time', 'N/A')}, "
                f"Returned: {rental.get('return_time', 'not yet returned')}. "
                f"Duration: {rental.get('duration_hours', 'N/A')} hours. "
                f"Renter: {rental.get('renter_name', 'N/A')}"
            )
            documents.append(doc)
            metadata_list.append({'type': 'rental', 'bicycle_id': bicycle_id, 'rental_id': rental.get('id')})

        if documents:
            self.vector_store.add_documents(documents, metadata_list)
            self.vector_store.save()
            logger.info(f"Indexed {len(documents)} records for bike #{bicycle_id}")

