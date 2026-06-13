import requests
import logging
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('ollama-client')

IST = timezone(timedelta(hours=5, minutes=30))


class OllamaClient:
    def __init__(self, base_url, model='tinyllama'):
        self.base_url = base_url.rstrip('/')
        self.model = model

    def generate(self, prompt, system_prompt=None):
        """Generate a response using Ollama LLM with data-driven validation"""
        # Always build a data-driven answer first
        data_answer = self._build_data_answer(prompt)

        # Try LLM for a natural language enhancement
        try:
            payload = {
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'num_predict': 512
                }
            }
            if system_prompt:
                payload['system'] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300
            )

            if response.status_code == 200:
                result = response.json()
                llm_answer = result.get('response', '').strip()

                # Validate LLM answer — if it's generic/empty, use data answer
                if self._is_generic_answer(llm_answer):
                    return data_answer
                return llm_answer
            else:
                return data_answer

        except Exception as e:
            logger.warning(f"Ollama unavailable ({e}), using data-driven response")
            return data_answer

    def _is_generic_answer(self, answer):
        """Check if LLM gave a generic non-data-grounded answer"""
        if not answer or len(answer) < 20:
            return True
        generic_phrases = [
            "i would recommend",
            "i don't have access",
            "no relevant history",
            "cannot provide",
            "i'm unable to",
            "based on the provided context and the fact that there are no",
            "reach out to the fleet manager",
            "consider reaching out",
        ]
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in generic_phrases)

    def _build_data_answer(self, prompt):
        """Build an intelligent answer directly from the context data"""
        context_start = prompt.find("--- CONTEXT ---")
        context_end = prompt.find("--- END CONTEXT ---")
        question_start = prompt.find("Staff Question:")
        bike_id_match = re.search(r"bicycle ID:\s*(\d+)", prompt)

        context = ""
        question = ""
        bike_id = None

        if context_start != -1 and context_end != -1:
            context = prompt[context_start + 15:context_end].strip()
        if question_start != -1:
            question = prompt[question_start + 15:].split("\n")[0].strip()
        if bike_id_match:
            bike_id = bike_id_match.group(1)

        if not context or context == "No relevant history found.":
            if bike_id:
                return (
                    f"No maintenance or rental history found for Bike #{bike_id}. "
                    f"This bike has not been rented or serviced yet. "
                    f"No maintenance is needed at this time based on available records."
                )
            return (
                "No relevant maintenance or rental records found for this query. "
                "Please add rental and maintenance data first."
            )

        # Parse records from context
        records = [r.strip() for r in context.split("\n\n") if r.strip()]
        maintenance_records = [r for r in records if "Maintenance" in r]
        rental_records = [r for r in records if "Rental" in r]
        anomalous_records = [r for r in records if "ANOMALOUS" in r]

        q_lower = question.lower()

        # --- Answer specific question types ---

        # "What problems has this bike had?" / "maintenance history"
        if "problem" in q_lower or "history" in q_lower or "past" in q_lower or "maintenance" in q_lower:
            return self._answer_maintenance_history(bike_id, maintenance_records, rental_records, anomalous_records)

        # "Does this bike need maintenance soon?" / "need servicing"
        if "need" in q_lower or "servic" in q_lower or "soon" in q_lower or "due" in q_lower:
            return self._answer_needs_service(bike_id, maintenance_records, rental_records)

        # "Which bikes haven't been serviced in 30 days?" / fleet-wide
        if "which" in q_lower or "haven't" in q_lower or "30 days" in q_lower or "high rental" in q_lower:
            return self._answer_fleet_query(maintenance_records, rental_records)

        # "Most common issue" / "common problem"
        if "common" in q_lower or "issue" in q_lower or "frequent" in q_lower:
            return self._answer_common_issues(maintenance_records)

        # "Summary" / general
        if "summary" in q_lower or "tell me" in q_lower or "overview" in q_lower:
            return self._answer_maintenance_history(bike_id, maintenance_records, rental_records, anomalous_records)

        # Default: provide a full data summary
        return self._answer_maintenance_history(bike_id, maintenance_records, rental_records, anomalous_records)

    def _answer_maintenance_history(self, bike_id, maintenance_records, rental_records, anomalous_records):
        """Answer questions about a bike's maintenance history"""
        parts = []
        bike_label = f"Bike #{bike_id}" if bike_id else "the fleet"

        if maintenance_records:
            parts.append(f"📋 **Maintenance History for {bike_label}:**\n")
            for i, rec in enumerate(maintenance_records[:5], 1):
                # Extract date
                date_match = re.search(r"Maintenance on (.+?):", rec)
                date_str = date_match.group(1) if date_match else "Unknown date"
                # Extract problem
                prob_match = re.search(r"Problem:\s*(.+?)\.\s*Work done:", rec)
                problem = prob_match.group(1) if prob_match else "Details not available"
                # Extract work done
                work_match = re.search(r"Work done:\s*(.+?)\.\s*Technician:", rec)
                work = work_match.group(1) if work_match else ""
                # Extract cost
                cost_match = re.search(r"Cost:\s*₹(\d+\.?\d*)", rec)
                cost = f"₹{cost_match.group(1)}" if cost_match else ""
                # Extract technician
                tech_match = re.search(r"Technician:\s*(.+?)\.", rec)
                tech = tech_match.group(1) if tech_match else ""

                parts.append(f"  {i}. **{date_str}**")
                parts.append(f"     Problem: {problem}")
                if work:
                    parts.append(f"     Work Done: {work}")
                if tech:
                    parts.append(f"     Technician: {tech} | Cost: {cost}")
                parts.append("")
        else:
            parts.append(f"No maintenance records found for {bike_label}.")

        if rental_records:
            parts.append(f"\n🚲 **Rental Activity:** {len(rental_records)} rental(s) recorded.")
            if anomalous_records:
                parts.append(f"⚠️ {len(anomalous_records)} anomalous (unusually short) rental(s) detected.")

        return "\n".join(parts)

    def _answer_needs_service(self, bike_id, maintenance_records, rental_records):
        """Answer whether a bike needs servicing soon"""
        parts = []
        bike_label = f"Bike #{bike_id}" if bike_id else "This bike"

        if not maintenance_records and not rental_records:
            return f"{bike_label} has no maintenance or rental history. No service needed at this time."

        if not maintenance_records and rental_records:
            parts.append(f"⚠️ **{bike_label} needs servicing!**")
            parts.append(f"")
            parts.append(f"Reason: {len(rental_records)} rental(s) recorded but NO maintenance has ever been performed.")
            parts.append(f"Recommendation: Schedule maintenance inspection immediately.")
            return "\n".join(parts)

        if maintenance_records:
            # Get latest service date
            latest_date = "recently"
            date_match = re.search(r"Maintenance on (.+?):", maintenance_records[0])
            if date_match:
                latest_date = date_match.group(1)

            rental_count = len(rental_records)
            maint_count = len(maintenance_records)

            parts.append(f"📊 **Service Assessment for {bike_label}:**\n")
            parts.append(f"  • Last serviced: {latest_date}")
            parts.append(f"  • Total maintenance records: {maint_count}")
            parts.append(f"  • Total rentals: {rental_count}")

            # Simple heuristic: if many rentals since last service
            if rental_count > maint_count * 3:
                parts.append(f"\n⚠️ **Recommendation: Service recommended.**")
                parts.append(f"   High rental-to-service ratio ({rental_count} rentals vs {maint_count} services).")
                parts.append(f"   Schedule preventive maintenance soon.")
            else:
                parts.append(f"\n✅ **Status: No immediate service needed.**")
                parts.append(f"   Rental-to-service ratio is acceptable.")
                parts.append(f"   Continue monitoring via risk scores on the dashboard.")

        return "\n".join(parts)

    def _answer_fleet_query(self, maintenance_records, rental_records):
        """Answer fleet-wide queries about which bikes need attention"""
        parts = []

        # Group records by bike ID
        bike_maintenance = {}
        bike_rentals = {}

        for rec in maintenance_records:
            bike_match = re.search(r"Bike #(\d+)", rec)
            if bike_match:
                bid = bike_match.group(1)
                bike_maintenance.setdefault(bid, []).append(rec)

        for rec in rental_records:
            bike_match = re.search(r"Bike #(\d+)", rec)
            if bike_match:
                bid = bike_match.group(1)
                bike_rentals.setdefault(bid, []).append(rec)

        parts.append("📊 **Fleet Maintenance Analysis:**\n")

        # Find bikes with high rentals but low/no maintenance
        needs_attention = []
        for bid, rentals in bike_rentals.items():
            maint_count = len(bike_maintenance.get(bid, []))
            rental_count = len(rentals)
            if rental_count > maint_count * 2:
                needs_attention.append((bid, rental_count, maint_count))

        if needs_attention:
            needs_attention.sort(key=lambda x: x[1], reverse=True)
            parts.append("⚠️ **Bikes needing attention (high rentals, low maintenance):**\n")
            for bid, rentals, maints in needs_attention[:5]:
                parts.append(f"  • Bike #{bid}: {rentals} rental(s), only {maints} service(s)")
            parts.append(f"\n📋 Recommendation: Prioritize these bikes for inspection.")
        else:
            parts.append("✅ All bikes in retrieved records have acceptable maintenance-to-rental ratios.")

        # Show summary
        all_bikes = set(list(bike_maintenance.keys()) + list(bike_rentals.keys()))
        parts.append(f"\n📈 Fleet summary from retrieved records: {len(all_bikes)} bike(s), "
                     f"{len(maintenance_records)} maintenance record(s), {len(rental_records)} rental(s).")

        return "\n".join(parts)

    def _answer_common_issues(self, maintenance_records):
        """Answer questions about most common issues"""
        if not maintenance_records:
            return "No maintenance records found to analyze common issues."

        parts = []
        parts.append("📊 **Most Common Issues Across Fleet:**\n")

        # Extract problems and categorize
        issues = []
        for rec in maintenance_records:
            prob_match = re.search(r"Problem:\s*(.+?)\.\s*Work done:", rec)
            if prob_match:
                issues.append(prob_match.group(1).lower())

        # Simple keyword categorization
        categories = {
            "Tyre/Puncture Issues": ["tyre", "puncture", "tube", "flat", "tire"],
            "Brake Problems": ["brake", "braking", "pad"],
            "Chain/Gear Issues": ["chain", "gear", "derailleur", "shifting", "cassette"],
            "General Service": ["service", "general", "quarterly", "full"],
            "Structural Issues": ["seat", "headset", "spoke", "wheel", "frame", "handlebar"],
        }

        category_counts = {}
        for issue in issues:
            for cat, keywords in categories.items():
                if any(kw in issue for kw in keywords):
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                    break

        if category_counts:
            sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (cat, count) in enumerate(sorted_cats, 1):
                parts.append(f"  {i}. **{cat}** — {count} occurrence(s)")
        else:
            parts.append("  Unable to categorize issues from available records.")

        parts.append(f"\n📋 Based on {len(maintenance_records)} maintenance record(s) analyzed.")
        parts.append(f"   Recommendation: Stock spare parts for the top issues listed above.")

        return "\n".join(parts)

    def is_available(self):
        """Check if Ollama server is reachable"""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

