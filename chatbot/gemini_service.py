# chatbot/gemini_service.py
import google.generativeai as genai
from django.conf import settings
from django.db.models import Sum
import json
from typing import Dict, Any

class GeminiChatService:
    def __init__(self):
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            self.system_prompt = self._create_system_prompt()
            print("✅ Service Gemini initialisé avec succès")
        except Exception as e:
            print(f"❌ Erreur initialisation Gemini: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        return """
        Tu es un expert comptable IA pour ComptaFlow. Tu aides avec:

        DOMAINES COMPTABLES:
        - Bilans comptables (Actif/Passif)
        - Comptes de résultat
        - Grand livre et journal
        - Plan comptable général (PCG)
        - Balance des comptes
        - Écritures comptables
        - Analyse financière

        RÈGLES COMPTABLES:
        - Classe 1: Capitaux propres
        - Classe 2: Immobilisations  
        - Classe 3: Stocks
        - Classe 4: Tiers (clients, fournisseurs)
        - Classe 5: Financier
        - Classe 6: Charges
        - Classe 7: Produits
        - Bilan équilibré: Total Actif = Total Passif
        - Résultat = Produits - Charges

        Sois précis, professionnel et utile.
        Si tu ne sais pas quelque chose, indique-le clairement.
        Réponds en français de manière structurée.
        """

    def get_accounting_context(self) -> str:
        """Récupère le contexte depuis la base de données"""
        try:
            from accounting.models import Account, Entry  # Adaptez selon vos models
            
            context_parts = []
            
            # Comptes principaux
            accounts = Account.objects.all()[:15]
            account_info = []
            for account in accounts:
                account_info.append(f"{account.number} - {account.name} ({account.type})")
            
            if account_info:
                context_parts.append("COMPTES DISPONIBLES:\n" + "\n".join(account_info))
            
            # Statistiques de base
            total_accounts = Account.objects.count()
            total_entries = Entry.objects.count()
            context_parts.append(f"STATISTIQUES: {total_accounts} comptes, {total_entries} écritures")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            return f"Contexte limité: {str(e)}"

    def send_message(self, user_message: str, conversation_history: list = None) -> Dict[str, Any]:
        """Envoie un message à Gemini"""
        try:
            # Récupérer le contexte comptable
            accounting_context = self.get_accounting_context()
            
            # Préparer l'historique
            history_text = ""
            if conversation_history:
                for msg in conversation_history[-4:]:
                    role = "Utilisateur" if msg.get('is_user', True) else "Assistant"
                    history_text += f"{role}: {msg.get('text', '')}\n\n"

            # Construire le prompt complet
            full_prompt = f"""
            {self.system_prompt}

            CONTEXTE COMPTABLE ACTUEL:
            {accounting_context}

            HISTORIQUE RÉCENT:
            {history_text if history_text else "Aucun historique récent."}

            QUESTION UTILISATEUR:
            {user_message}

            RÉPONSE (sois concis et professionnel):
            """

            # Générer la réponse
            response = self.model.generate_content(full_prompt)
            
            return {
                'success': True,
                'message': response.text,
                'model': 'gemini-pro'
            }
            
        except Exception as e:
            print(f"❌ Erreur Gemini: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Désolé, je rencontre une difficulté technique. Veuillez réessayer.'
            }

# Instance globale
gemini_service = GeminiChatService()