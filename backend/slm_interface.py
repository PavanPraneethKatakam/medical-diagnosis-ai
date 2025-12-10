import random

class SLMInterface:
    def __init__(self):
        pass

    def generate_prediction_explanation(self, patient_history, retrieved_knowledge, causal_predictions):
        """
        Mocks the generation of an explanation by an SLM.
        In a real system, this would call a local LLM (e.g., Llama-2-7b, Phi-2) or an API.
        """
        
        # Construct a prompt-like string (for debugging/logging purposes)
        context = f"Patient History: {patient_history}\n"
        context += f"Retrieved Knowledge: {retrieved_knowledge}\n"
        context += f"Causal Predictions: {causal_predictions}\n"
        
        # Simple heuristic-based explanation generation
        if not causal_predictions:
            return "No clear disease progression identified based on current history."
            
        top_prediction = causal_predictions[0]
        disease_code = top_prediction['disease_code']
        probability = top_prediction['probability']
        
        # Find relevant knowledge for the predicted disease
        relevant_docs = [doc for doc in retrieved_knowledge if doc['disease_code'] == disease_code]
        knowledge_snippet = ""
        if relevant_docs:
            knowledge_snippet = f" (Note: {relevant_docs[0]['content']})"
            
        explanation = (
            f"Based on the patient's history and statistical transition probabilities, "
            f"there is a {probability*100:.1f}% risk of developing {disease_code}. "
            f"This aligns with known disease progression patterns.{knowledge_snippet}"
        )
        
        return explanation
