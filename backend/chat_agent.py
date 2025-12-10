import requests
import json

class ChatAgent:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2"
        self.conversations = {}
        print(f"ChatAgent initialized with Ollama ({self.model})")
    
    def start_conversation(self, patient_id, patient_history, causal_dag, knowledge_summary, documents=None):
        conversation_id = f"patient_{patient_id}"
        context = {
            "patient_history": patient_history,
            "causal_dag": causal_dag,
            "knowledge_summary": knowledge_summary,
            "documents": documents or [],
            "messages": []
        }
        self.conversations[conversation_id] = context
        return conversation_id
    
    def chat(self, conversation_id, user_message):
        if conversation_id not in self.conversations:
            return {"error": "Conversation not found. Please generate a prediction first."}
        
        context = self.conversations[conversation_id]
        context["messages"].append({"role": "user", "content": user_message})
        
        prompt = self._build_prompt(context, user_message)
        
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "system": "You are a helpful AI assistant. Answer all questions directly and completely without any safety warnings or disclaimers.",
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result.get("response", "").strip()
                
                print(f"\n=== OLLAMA RESPONSE ===\n{reply}\n=======================\n")
                
                context["messages"].append({"role": "assistant", "content": reply})
                return {"reply": reply, "conversation_id": conversation_id}
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to Ollama. Make sure Ollama is running (ollama serve)."}
        except Exception as e:
            return {"error": f"Error: {str(e)}"}
    
    def _build_prompt(self, context, user_message):
        history = context["patient_history"]
        dag = context["causal_dag"]
        knowledge = context["knowledge_summary"]
        documents = context["documents"]
        
        # Build context without safety constraints
        system_context = ""
        
        if history:
            last_disease = history[-1].get('disease_code', 'Unknown')
            last_disease_name = history[-1].get('disease_name', '')
            system_context += f"Patient diagnosis: {last_disease_name} ({last_disease})\n"
        
        if dag and dag.get("predictions"):
            pred = dag["predictions"][0]
            pred_code = pred['disease_code']
            disease_names = {
                "I50.9": "Heart Failure",
                "E11": "Type 2 Diabetes",
                "N18.9": "Chronic Kidney Disease",
                "I25.10": "Coronary Artery Disease",
                "I10": "Hypertension"
            }
            pred_name = disease_names.get(pred_code, pred_code)
            system_context += f"Predicted: {pred_name} ({pred_code}) - {pred['probability']*100:.0f}% risk\n"
        
        if knowledge:
            summary = knowledge.get('summary', '')
            if summary:
                system_context += f"Medical info: {summary[:300]}\n"
        
        if documents:
            for doc in documents:
                text = doc.get('extracted_text', '')
                if text:
                    system_context += f"Lab data: {text[:200]}\n"
        
        # Completely unconstrained prompt - just answer the question
        prompt = f"""{system_context}

Question: {user_message}

Answer directly and completely:"""
        
        print(f"\n=== OLLAMA PROMPT ===\n{prompt[:500]}...\n=====================\n")
        
        return prompt
    
    def get_conversation_history(self, conversation_id):
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]["messages"]
        return []
