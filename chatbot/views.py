import google.generativeai as genai
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import re
from datetime import datetime, timedelta
from .models import ChatConversation, ChatMessage
from django.contrib.auth.models import User

class AccountingChatBotView(View):
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.gemini_available = False
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialise Gemini avec les modèles actuels"""
        try:
            print("🔧 Début de l'initialisation Gemini...")
            
            # Vérification clé API
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                print("❌ Clé API Gemini non configurée dans settings.py")
                return
            
            print(f"✅ Clé API trouvée: {settings.GEMINI_API_KEY[:10]}...")
            
            # Configurer Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            print("✅ Gemini configuré avec la clé API")
            
            # LISTE DES MODÈLES ACTUALISÉE
            models_to_try = [
                'gemini-2.0-flash',
                'gemini-2.0-flash-001',
                'gemini-flash-latest',
                'gemini-2.0-flash-lite',
                'gemini-pro-latest',
            ]
            
            print(f"🔄 Test de {len(models_to_try)} modèles...")
            
            for model_name in models_to_try:
                try:
                    print(f"🔄 Test du modèle: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    test_response = self.model.generate_content("Réponds juste par 'OK'")
                    
                    if test_response and test_response.text:
                        self.gemini_available = True
                        print(f"✅ Gemini initialisé avec: {model_name}")
                        print(f"✅ Test réponse: {test_response.text}")
                        return
                        
                except Exception as e:
                    print(f"❌ {model_name} échoué: {str(e)[:100]}...")
                    continue
            
            print("❌ Aucun modèle disponible")
            self.gemini_available = False
                
        except Exception as e:
            print(f"💥 Erreur initialisation: {str(e)}")
            self.gemini_available = False

    def get_gemini_status(self):
        """Méthode pour diagnostiquer l'état de Gemini"""
        status = {
            'gemini_available': self.gemini_available,
            'model_loaded': self.model is not None,
            'api_key_configured': hasattr(settings, 'GEMINI_API_KEY') and bool(settings.GEMINI_API_KEY),
            'api_key_value': '***' + settings.GEMINI_API_KEY[-4:] if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY else None
        }
        return status

    def generate_sql_with_gemini(self, user_question):
        """Utilise Gemini pour générer une requête SQL avec un prompt complet et professionnel"""
        if not self.gemini_available or not self.model:
            print("❌ Gemini non disponible pour cette requête")
            return None
        
        try:
            # PROMPT PROFESSIONNEL COMPLET avec TOUTES les requêtes possibles
            prompt = f"""
            Tu es un expert SQL et comptable français professionnel. Génère UNIQUEMENT une requête SQL PostgreSQL pour répondre à cette question comptable.

            QUESTION: "{user_question}"

            STRUCTURE DE LA BASE DE DONNÉES:

            ### Table: accounting_account
            - id (INTEGER, clé primaire)
            - numero (VARCHAR(20)) - numéro du compte (ex: '411000')
            - intitule (VARCHAR(100)) - intitulé du compte
            - classe (INTEGER) - classe comptable (1-8)
            - type (VARCHAR(20)) - 'Actif', 'Passif', 'Charge', 'Produit', 'TVA', 'Autre'
            - nature (VARCHAR(100)) - nature du compte
            - "soldeInitial" (DECIMAL(12,2)) - solde initial

            ### Table: accounting_journalentry
            - id (INTEGER, clé primaire)
            - date (DATE) - date de l'écriture
            - libelle (VARCHAR(200)) - libellé de l'opération
            - reference (VARCHAR(100)) - référence
            - "numeroEcriture" (VARCHAR(50)) - numéro d'écriture
            - nature (VARCHAR(100)) - nature de l'opération

            ### Table: accounting_transactionline
            - id (INTEGER, clé primaire)
            - journal_entry_id (INTEGER) - clé étrangère vers accounting_journalentry
            - account_id (INTEGER) - clé étrangère vers accounting_account
            - debit (DECIMAL(12,2)) - montant débit
            - credit (DECIMAL(12,2)) - montant crédit
            - accountNumber (VARCHAR(32)) - numéro de compte
            - accountName (VARCHAR(128)) - nom du compte

            ### RÈGLES IMPORTANTES:
            1. UTILISE UNIQUEMENT des requêtes SELECT
            2. Les noms de tables EXACTS sont: accounting_account, accounting_journalentry, accounting_transactionline
            3. Pour "numeroEcriture" et "soldeInitial", UTILISE des guillemets: "numeroEcriture", "soldeInitial"
            4. Sois TRÈS PRÉCIS dans les conditions WHERE
            5. Utilise des fonctions d'agrégation: SUM(), COUNT(), AVG(), MAX(), MIN()
            6. Pour les recherches textuelles, utilise ILIKE avec % pour les recherches partielles
            7. Pour les jointures: JOIN accounting_account ON accounting_transactionline.account_id = accounting_account.id
            8. Formate la réponse UNIQUEMENT avec: ```sql [ta_requête_sql] ```

            ### CATÉGORIE 1: SOLDE ET INFORMATIONS DES COMPTES
            Question: "Quel est le solde du compte 411000 ?"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.numero = '411000' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Donne-moi le solde du compte Clients"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.intitule ILIKE '%Clients%' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Affiche le solde du compte 512000"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.numero = '512000' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Quel est le montant du compte 445660 ?"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.numero = '445660' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Montre-moi le solde initial du compte 106000"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE numero = '106000'; ```

            ### CATÉGORIE 2: RECHERCHE DE COMPTES
            Question: "Trouve le compte 411000"
            Réponse: ```sql SELECT numero, intitule, type, classe, "soldeInitial" FROM accounting_account WHERE numero = '411000'; ```

            Question: "Donne-moi les informations du compte Banque"
            Réponse: ```sql SELECT numero, intitule, type, classe, "soldeInitial" FROM accounting_account WHERE intitule ILIKE '%Banque%'; ```

            Question: "Recherche les comptes de charges"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'Charge' ORDER BY numero; ```

            Question: "Liste tous les comptes de produits"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'Produit' ORDER BY numero; ```

            Question: "Affiche les comptes de la classe 4"
            Réponse: ```sql SELECT numero, intitule, type FROM accounting_account WHERE classe = 4 ORDER BY numero; ```

            Question: "Quels sont les comptes d'actif ?"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'Actif' ORDER BY numero; ```

            Question: "Montre-moi les comptes de passif"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'Passif' ORDER BY numero; ```

            Question: "Liste les comptes de TVA"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'TVA' ORDER BY numero; ```

            ### CATÉGORIE 3: ANALYSE PAR TYPE DE COMPTE
            Question: "Combien y a-t-il de comptes de charge ?"
            Réponse: ```sql SELECT COUNT(*) as nombre_comptes FROM accounting_account WHERE type = 'Charge'; ```

            Question: "Nombre de comptes d'actif"
            Réponse: ```sql SELECT COUNT(*) as nombre_comptes FROM accounting_account WHERE type = 'Actif'; ```

            Question: "Quels sont les comptes de produits ?"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'Produit' ORDER BY numero; ```

            Question: "Liste les comptes de TVA disponibles"
            Réponse: ```sql SELECT numero, intitule, classe FROM accounting_account WHERE type = 'TVA' ORDER BY numero; ```

            ### CATÉGORIE 4: TOTAUX GÉNÉRAUX
            Question: "Quel est le total des débits ?"
            Réponse: ```sql SELECT SUM(debit) as total_debits FROM accounting_transactionline; ```

            Question: "Quel est le total des crédits ?"
            Réponse: ```sql SELECT SUM(credit) as total_credits FROM accounting_transactionline; ```

            Question: "Donne-moi le solde général"
            Réponse: ```sql SELECT SUM(debit) as total_debits, SUM(credit) as total_credits, SUM(debit) - SUM(credit) as solde_general FROM accounting_transactionline; ```

            Question: "Total des mouvements du mois"
            Réponse: ```sql SELECT SUM(debit) as total_debits, SUM(credit) as total_credits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('month', CURRENT_DATE) AND j.date < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month'); ```

            Question: "Montre le total des transactions"
            Réponse: ```sql SELECT COUNT(*) as nombre_transactions FROM accounting_transactionline; ```

            ### CATÉGORIE 5: ANALYSE PAR PÉRIODE
            Question: "Total des débits du mois dernier"
            Réponse: ```sql SELECT SUM(debit) as total_debits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND j.date < DATE_TRUNC('month', CURRENT_DATE); ```

            Question: "Total des crédits du mois en cours"
            Réponse: ```sql SELECT SUM(credit) as total_credits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('month', CURRENT_DATE) AND j.date < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month'); ```

            Question: "Débits de la semaine dernière"
            Réponse: ```sql SELECT SUM(debit) as total_debits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= CURRENT_DATE - INTERVAL '7 days' AND j.date < CURRENT_DATE; ```

            Question: "Transactions du trimestre"
            Réponse: ```sql SELECT SUM(debit) as total_debits, SUM(credit) as total_credits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('quarter', CURRENT_DATE) AND j.date < DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months'; ```

            Question: "Mouvements de l'année 2024"
            Réponse: ```sql SELECT SUM(debit) as total_debits, SUM(credit) as total_credits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE EXTRACT(YEAR FROM j.date) = 2024; ```

            ### CATÉGORIE 6: PAR COMPTE SPÉCIFIQUE
            Question: "Total des débits du compte 411000"
            Réponse: ```sql SELECT SUM(debit) as total_debits FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id WHERE a.numero = '411000'; ```

            Question: "Crédits du compte 512000 ce mois"
            Réponse: ```sql SELECT SUM(credit) as total_credits FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.numero = '512000' AND j.date >= DATE_TRUNC('month', CURRENT_DATE); ```

            Question: "Mouvements du compte Clients"
            Réponse: ```sql SELECT j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.intitule ILIKE '%Clients%' ORDER BY j.date DESC; ```

            Question: "Transactions du compte Banque"
            Réponse: ```sql SELECT j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.intitule ILIKE '%Banque%' ORDER BY j.date DESC; ```

            ### CATÉGORIE 7: RECHERCHE D'ÉCRITURES
            Question: "Liste les 10 dernières écritures"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC, id DESC LIMIT 10; ```

            Question: "Affiche les 5 écritures les plus récentes"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 5; ```

            Question: "Donne-moi toutes les écritures d'hier"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE date = CURRENT_DATE - INTERVAL '1 day' ORDER BY date DESC; ```

            Question: "Écritures du mois de janvier"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE EXTRACT(YEAR FROM date) = 2024 AND EXTRACT(MONTH FROM date) = 1 ORDER BY date DESC; ```

            Question: "Recherche les écritures avec 'Client Dupont'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Client Dupont%' ORDER BY date DESC; ```

            Question: "Trouve les écritures contenant 'Facture'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Facture%' ORDER BY date DESC; ```

            Question: "Écritures avec la référence 'FAC2024001'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE reference ILIKE '%FAC2024001%' ORDER BY date DESC; ```

            ### CATÉGORIE 8: ANALYSE DES ÉCRITURES
            Question: "Combien d'écritures ce mois-ci ?"
            Réponse: ```sql SELECT COUNT(*) as nombre_ecritures FROM accounting_journalentry WHERE date >= DATE_TRUNC('month', CURRENT_DATE) AND date < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month'); ```

            Question: "Nombre d'écritures par jour"
            Réponse: ```sql SELECT date, COUNT(*) as nombre_ecritures FROM accounting_journalentry GROUP BY date ORDER BY date DESC; ```

            Question: "Dernière écriture enregistrée"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC, id DESC LIMIT 1; ```

            Question: "Écritures du journal de banque"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%banque%' OR libelle ILIKE '%chèque%' OR libelle ILIKE '%virement%' ORDER BY date DESC; ```

            ### CATÉGORIE 9: PAR CLASSE COMPTABLE
            Question: "Liste les comptes de classe 1"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 1 ORDER BY numero; ```

            Question: "Solde total de la classe 1"
            Réponse: ```sql SELECT SUM(COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0)) as solde_total FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.classe = 1 GROUP BY a.id; ```

            Question: "Comptes de capitaux propres"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 1 AND numero LIKE '10%' ORDER BY numero; ```

            Question: "Affiche les comptes de classe 2"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 2 ORDER BY numero; ```

            Question: "Immobilisations de l'entreprise"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 2 ORDER BY numero; ```

            Question: "Comptes d'amortissement"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 2 AND numero LIKE '28%' ORDER BY numero; ```

            Question: "Comptes de stocks disponibles"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 3 ORDER BY numero; ```

            Question: "Liste la classe 3"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 3 ORDER BY numero; ```

            Question: "Valeur des stocks"
            Réponse: ```sql SELECT SUM("soldeInitial") as valeur_stocks FROM accounting_account WHERE classe = 3; ```

            Question: "Tous les comptes fournisseurs"
            Réponse: ```sql SELECT numero, intitule, type FROM accounting_account WHERE classe = 4 AND numero LIKE '4%' ORDER BY numero; ```

            Question: "Liste des comptes clients"
            Réponse: ```sql SELECT numero, intitule, type FROM accounting_account WHERE classe = 4 AND numero LIKE '41%' ORDER BY numero; ```

            Question: "Comptes de personnel classe 4"
            Réponse: ```sql SELECT numero, intitule, type FROM accounting_account WHERE classe = 4 AND numero LIKE '42%' OR numero LIKE '43%' ORDER BY numero; ```

            Question: "Comptes bancaires disponibles"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 5 ORDER BY numero; ```

            Question: "Liste des comptes de banque"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 5 ORDER BY numero; ```

            Question: "Comptes financiers classe 5"
            Réponse: ```sql SELECT numero, intitule, type, "soldeInitial" FROM accounting_account WHERE classe = 5 ORDER BY numero; ```

            Question: "Toutes les charges de l'entreprise"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 6 ORDER BY numero; ```

            Question: "Liste des comptes de charge"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 6 ORDER BY numero; ```

            Question: "Charges par type"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 6 ORDER BY numero; ```

            Question: "Comptes de produits d'exploitation"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 7 ORDER BY numero; ```

            Question: "Liste des produits"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 7 ORDER BY numero; ```

            Question: "Ventes et autres produits"
            Réponse: ```sql SELECT numero, intitule, "soldeInitial" FROM accounting_account WHERE classe = 7 ORDER BY numero; ```

            ### CATÉGORIE 10: TOP ET CLASSEMENTS
            Question: "Quels sont les 10 comptes les plus utilisés ?"
            Réponse: ```sql SELECT a.numero, a.intitule, COUNT(t.id) as usage_count FROM accounting_account a JOIN accounting_transactionline t ON a.id = t.account_id GROUP BY a.id, a.numero, a.intitule ORDER BY usage_count DESC LIMIT 10; ```

            Question: "Top 5 des comptes avec le plus de transactions"
            Réponse: ```sql SELECT a.numero, a.intitule, COUNT(t.id) as nombre_transactions FROM accounting_account a JOIN accounting_transactionline t ON a.id = t.account_id GROUP BY a.id, a.numero, a.intitule ORDER BY nombre_transactions DESC LIMIT 5; ```

            Question: "Comptes avec le plus grand solde"
            Réponse: ```sql SELECT a.numero, a.intitule, ABS(COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0)) as solde_absolu FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id GROUP BY a.id, a.numero, a.intitule ORDER BY solde_absolu DESC LIMIT 10; ```

            Question: "Comptes les plus actifs ce mois"
            Réponse: ```sql SELECT a.numero, a.intitule, COUNT(t.id) as activite FROM accounting_account a JOIN accounting_transactionline t ON a.id = t.account_id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY a.id, a.numero, a.intitule ORDER BY activite DESC LIMIT 10; ```

            ### CATÉGORIE 11: STATISTIQUES
            Question: "Nombre total de comptes"
            Réponse: ```sql SELECT COUNT(*) as total_comptes FROM accounting_account; ```

            Question: "Nombre total d'écritures"
            Réponse: ```sql SELECT COUNT(*) as total_ecritures FROM accounting_journalentry; ```

            Question: "Nombre total de transactions"
            Réponse: ```sql SELECT COUNT(*) as nombre_transactions FROM accounting_transactionline; ```

            Question: "Moyenne des montants de débit"
            Réponse: ```sql SELECT AVG(debit) as moyenne_debit FROM accounting_transactionline WHERE debit > 0; ```

            Question: "Plus gros montant de crédit"
            Réponse: ```sql SELECT MAX(credit) as max_credit FROM accounting_transactionline; ```

            Question: "Distribution des montants de débit"
            Réponse: ```sql SELECT COUNT(*) as nombre_transactions, AVG(debit) as moyenne, MAX(debit) as maximum, MIN(debit) as minimum FROM accounting_transactionline WHERE debit > 0; ```

            ### CATÉGORIE 12: RECHERCHES COMPLEXES
            Question: "Trouve les écritures sans référence"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle FROM accounting_journalentry WHERE reference IS NULL OR reference = '' ORDER BY date DESC; ```

            Question: "Comptes sans mouvement ce mois"
            Réponse: ```sql SELECT a.numero, a.intitule FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id LEFT JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date IS NULL OR j.date < DATE_TRUNC('month', CURRENT_DATE) GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Écritures avec des libellés vides"
            Réponse: ```sql SELECT "numeroEcriture", date, reference FROM accounting_journalentry WHERE libelle IS NULL OR libelle = ''; ```

            Question: "Transactions avec des montants anormaux"
            Réponse: ```sql SELECT j."numeroEcriture", j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE t.debit > 100000 OR t.credit > 100000 ORDER BY j.date DESC; ```

            ### CATÉGORIE 13: RECHERCHE TEXTUELLE
            Question: "Recherche 'Client Martin' dans les libellés"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Client Martin%' ORDER BY date DESC; ```

            Question: "Trouve les écritures avec 'Salaire'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Salaire%' ORDER BY date DESC; ```

            Question: "Écritures contenant 'Remboursement'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Remboursement%' ORDER BY date DESC; ```

            Question: "Recherche 'Achat' dans les libellés"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Achat%' ORDER BY date DESC; ```

            Question: "Trouve l'écriture avec la référence 'FAC-001'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE reference ILIKE '%FAC-001%' ORDER BY date DESC; ```

            Question: "Recherche par référence 'BQ2024'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE reference ILIKE '%BQ2024%' ORDER BY date DESC; ```

            Question: "Écritures avec référence commençant par 'CH'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE reference LIKE 'CH%' ORDER BY date DESC; ```

            ### CATÉGORIE 14: TEMPOREL - PAR DATE SPÉCIFIQUE
            Question: "Écritures du 15 janvier 2024"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE date = '2024-01-15' ORDER BY date DESC; ```

            Question: "Transactions d'hier"
            Réponse: ```sql SELECT j."numeroEcriture", j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date = CURRENT_DATE - INTERVAL '1 day'; ```

            Question: "Mouvements de la semaine dernière"
            Réponse: ```sql SELECT j."numeroEcriture", j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= CURRENT_DATE - INTERVAL '7 days' AND j.date < CURRENT_DATE ORDER BY j.date DESC; ```

            ### CATÉGORIE 15: PÉRIODES PERSONNALISÉES
            Question: "Écritures entre le 1er janvier et le 31 mars 2024"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE date BETWEEN '2024-01-01' AND '2024-03-31' ORDER BY date DESC; ```

            Question: "Transactions des 30 derniers jours"
            Réponse: ```sql SELECT j."numeroEcriture", j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= CURRENT_DATE - INTERVAL '30 days' ORDER BY j.date DESC; ```

            Question: "Mouvements du dernier trimestre"
            Réponse: ```sql SELECT j."numeroEcriture", j.date, j.libelle, t.debit, t.credit FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months') AND j.date < DATE_TRUNC('quarter', CURRENT_DATE) ORDER BY j.date DESC; ```

            ### CATÉGORIE 16: SITUATION CLIENT/FOURNISSEUR
            Question: "Situation du client Dupont"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) as total_debit, COALESCE(SUM(t.credit), 0) as total_credit, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.intitule ILIKE '%Dupont%' AND a.type = 'Actif' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Solde fournisseur Martin"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.intitule ILIKE '%Martin%' AND a.type = 'Passif' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Historique des transactions avec un client"
            Réponse: ```sql SELECT j.date, j.libelle, t.debit, t.credit, j."numeroEcriture" FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.intitule ILIKE '%Martin%' ORDER BY j.date DESC; ```

            ### CATÉGORIE 17: ANALYSE FINANCIÈRE
            Question: "Bilan simplifié (actif/passif)"
            Réponse: ```sql SELECT type, COUNT(*) as nombre_comptes, SUM("soldeInitial") as solde_initial_total, SUM(COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0)) as solde_courant FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE type IN ('Actif', 'Passif') GROUP BY type; ```

            Question: "Total des charges du mois"
            Réponse: ```sql SELECT SUM(t.debit) as total_charges FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.type = 'Charge' AND j.date >= DATE_TRUNC('month', CURRENT_DATE); ```

            Question: "Total des produits du trimestre"
            Réponse: ```sql SELECT SUM(t.credit) as total_produits FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE a.type = 'Produit' AND j.date >= DATE_TRUNC('quarter', CURRENT_DATE) AND j.date < DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months'; ```

            Question: "Marge brute"
            Réponse: ```sql SELECT (SELECT SUM(t.credit) FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id WHERE a.type = 'Produit') - (SELECT SUM(t.debit) FROM accounting_transactionline t JOIN accounting_account a ON t.account_id = a.id WHERE a.type = 'Charge') as marge_brute; ```

            ### CATÉGORIE 18: TECHNIQUE ET STRUCTURE
            Question: "Combien de tables dans la base ?"
            Réponse: ```sql SELECT COUNT(*) as nombre_tables FROM information_schema.tables WHERE table_schema = 'public'; ```

            Question: "Liste tous les noms de colonnes"
            Réponse: ```sql SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' ORDER BY table_name, ordinal_position; ```

            Question: "Structure de la table accounting_account"
            Réponse: ```sql SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'accounting_account' ORDER BY ordinal_position; ```

            Question: "Dernière écriture enregistrée"
            Réponse: ```sql SELECT MAX(date) as derniere_date FROM accounting_journalentry; ```

            Question: "Date de la première transaction"
            Réponse: ```sql SELECT MIN(date) as premiere_date FROM accounting_journalentry; ```

            Question: "Période couverte par les données"
            Réponse: ```sql SELECT MIN(date) as premiere_date, MAX(date) as derniere_date FROM accounting_journalentry; ```

            MAINTENANT, GÉNÈRE LA REQUÊTE SQL POUR CETTE QUESTION:
            """

            print(f"🧠 Envoi à Gemini: {user_question}")
            
            # Configuration de la génération pour plus de stabilité
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response.text:
                print(f"✅ Réponse Gemini reçue: {response.text[:200]}...")
                return response.text
            else:
                print("❌ Gemini n'a retourné aucune réponse")
                return None
                
        except Exception as e:
            print(f"💥 Erreur lors de l'appel à Gemini: {str(e)}")
            # Désactiver Gemini pour les prochaines requêtes
            self.gemini_available = False
            return None

    def get_intelligent_fallback_query(self, user_question):
        """Génère une requête SQL intelligente sans Gemini"""
        question_lower = user_question.lower()
        print(f"🔄 Utilisation du fallback intelligent pour: {user_question}")
        
        # Détection du numéro de compte
        compte_match = re.search(r'(\d{6})', user_question)
        if compte_match:
            numero_compte = compte_match.group(1)
            
            if any(word in question_lower for word in ['solde', 'balance', 'montant']):
                return f"""
                SELECT 
                    a.numero,
                    a.intitule, 
                    a.type,
                    COALESCE(SUM(t.debit), 0) as total_debit,
                    COALESCE(SUM(t.credit), 0) as total_credit,
                    COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde
                FROM accounting_account a
                LEFT JOIN accounting_transactionline t ON a.id = t.account_id
                WHERE a.numero = '{numero_compte}'
                GROUP BY a.id, a.numero, a.intitule, a.type;
                """
            else:
                return f"SELECT numero, intitule, type, classe, \"soldeInitial\" FROM accounting_account WHERE numero = '{numero_compte}';"
        
        # Recherche par type de compte
        type_mapping = {
            'actif': 'Actif',
            'passif': 'Passif', 
            'charge': 'Charge',
            'produit': 'Produit',
            'tva': 'TVA'
        }
        
        for type_key, type_value in type_mapping.items():
            if type_key in question_lower:
                if any(word in question_lower for word in ['combien', 'nombre', 'count']):
                    return f"SELECT COUNT(*) as nombre_comptes FROM accounting_account WHERE type = '{type_value}';"
                else:
                    return f"SELECT numero, intitule, classe FROM accounting_account WHERE type = '{type_value}' ORDER BY numero;"
        
        # Recherche par classe
        classe_match = re.search(r'classe\s*(\d)', question_lower)
        if classe_match:
            classe = classe_match.group(1)
            return f"SELECT numero, intitule, type FROM accounting_account WHERE classe = {classe} ORDER BY numero;"
        
        # Recherche textuelle dans les libellés
        libelle_match = re.search(r'["\'](.*?)["\']', user_question)
        if libelle_match:
            libelle = libelle_match.group(1)
            return f'SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE \'%{libelle}%\' ORDER BY date DESC;'
        
        # Questions générales
        if any(word in question_lower for word in ['solde', 'balance']) and 'compte' not in question_lower:
            return """
            SELECT 
                a.numero,
                a.intitule,
                a.type,
                COALESCE(SUM(t.debit), 0) as total_debit,
                COALESCE(SUM(t.credit), 0) as total_credit,
                COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde
            FROM accounting_account a
            LEFT JOIN accounting_transactionline t ON a.id = t.account_id
            GROUP BY a.id, a.numero, a.intitule, a.type
            ORDER BY a.numero;
            """
        
        # Fallback basé sur les mots-clés
        keyword_queries = {
            'débit': "SELECT SUM(debit) as total_debit FROM accounting_transactionline;",
            'debit': "SELECT SUM(debit) as total_debit FROM accounting_transactionline;",
            'crédit': "SELECT SUM(credit) as total_credit FROM accounting_transactionline;", 
            'credit': "SELECT SUM(credit) as total_credit FROM accounting_transactionline;",
            'écriture':"SELECT \"numeroEcriture\", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 10;",
            'journal': "SELECT \"numeroEcriture\", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 10;",
            'compte': "SELECT numero, intitule, type, classe FROM accounting_account ORDER BY numero LIMIT 20;",
            'account': "SELECT numero, intitule, type, classe FROM accounting_account ORDER BY numero LIMIT 20;"
        }
        
        for keyword, query in keyword_queries.items():
            if keyword in question_lower:
                return query
        
        # Fallback par défaut
        return "SELECT COUNT(*) as total_comptes FROM accounting_account;"

    def extract_sql_from_response(self, text):
        """Extrait et nettoie la requête SQL de la réponse"""
        if not text:
            return None
            
        patterns = [
            r"```sql\s*(.*?)\s*```",
            r"```\s*(SELECT.*?)\s*```",
            r"(SELECT\s+.*?;)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                sql = matches[0].strip()
                # Nettoyer la requête
                sql = sql.replace('```sql', '').replace('```', '').strip()
                
                # Nettoyer les guillemets problématiques
                sql = sql.replace('""', '"')
                sql = re.sub(r'\b"(\w+)"', r'"\1"', sql)
                
                print(f"✅ SQL extrait et nettoyé: {sql}")
                return sql
        
        return None

    def execute_safe_sql(self, sql_query):
        """Exécute une requête SQL de manière sécurisée"""
        try:
            if not sql_query:
                return None, "Requête SQL vide"
            
            # Nettoyer et corriger la requête
            sql_query = sql_query.strip()
            
            # Corriger les guillemets problématiques
            sql_query = sql_query.replace('""soldeInitial""', '"soldeInitial"')
            sql_query = sql_query.replace('""numeroEcriture""', '"numeroEcriture"')
            sql_query = re.sub(r'a\.""', 'a."', sql_query)
            sql_query = re.sub(r'j\.""', 'j."', sql_query)
            
            # Vérification de sécurité
            dangerous_keywords = ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            sql_upper = sql_query.upper()
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return None, f"Requête non autorisée: {keyword}"
            
            if not sql_upper.startswith('SELECT'):
                return None, "Seules les requêtes SELECT sont autorisées"
            
            print(f"🔍 Exécution SQL: {sql_query}")
            
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    results = cursor.fetchall()
                    
                    data = []
                    for row in results:
                        row_data = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            if isinstance(value, (datetime, timedelta)):
                                value = str(value)
                            row_data[col] = value
                        data.append(row_data)
                    
                    print(f"✅ Données récupérées: {len(data)} lignes")
                    return data, None
                else:
                    return [], "Aucun résultat"
                
        except Exception as e:
            error_msg = f"Erreur SQL: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"🔍 Requête problématique: {sql_query}")
            return None, error_msg

    def detect_result_type(self, data, user_question):
        """Détecte automatiquement le type de résultat pour un meilleur formatage"""
        if not data or len(data) == 0:
            return "empty"
        
        first_row = data[0]
        question_lower = user_question.lower()
        
        # Détection des totaux/sommes
        total_columns = [col for col in first_row.keys() if any(keyword in col.lower() for keyword in ['total', 'sum', 'montant', 'solde'])]
        if total_columns and len(data) == 1:
            return "total"
        
        # Détection des comptes
        if 'numero' in first_row and 'intitule' in first_row:
            return "accounts"
        
        # Détection des écritures
        if any(col in first_row for col in ['numeroEcriture', 'numeroecriture', 'libelle', 'date']):
            return "journal_entries"
        
        # Détection des counts
        count_columns = [col for col in first_row.keys() if any(keyword in col.lower() for keyword in ['count', 'nombre'])]
        if count_columns:
            return "count"
        
        return "generic"

    def format_response(self, data, user_question):
        """Formate une réponse contextuelle améliorée"""
        if not data:
            return f"❌ Aucune donnée trouvée pour: '{user_question}'"
        
        result_type = self.detect_result_type(data, user_question)
        first_row = data[0]
        
        if result_type == "total":
            # Trouver la colonne qui contient le total
            total_columns = [col for col in first_row.keys() if any(keyword in col.lower() for keyword in ['total', 'sum', 'montant', 'solde'])]
            if total_columns:
                total_col = total_columns[0]
                total_value = first_row[total_col] or 0
                
                # Adapter le message au contexte
                question_lower = user_question.lower()
                if 'débit' in question_lower or 'debit' in question_lower:
                    return f"💰 Total des débits: {float(total_value):,.2f} €"
                elif 'crédit' in question_lower or 'credit' in question_lower:
                    return f"💰 Total des crédits: {float(total_value):,.2f} €"
                elif 'charge' in question_lower:
                    return f"💰 Total des charges: {float(total_value):,.2f} €"
                elif 'produit' in question_lower:
                    return f"💰 Total des produits: {float(total_value):,.2f} €"
                elif 'solde' in question_lower and 'général' in question_lower:
                    return f"💰 Solde général: {float(total_value):,.2f} €"
                else:
                    return f"💰 Total: {float(total_value):,.2f} €"
        
        elif result_type == "count":
            count_columns = [col for col in first_row.keys() if any(keyword in col.lower() for keyword in ['count', 'nombre'])]
            if count_columns:
                count_value = first_row[count_columns[0]] or 0
                
                question_lower = user_question.lower()
                if 'compte' in question_lower and 'charge' in question_lower:
                    return f"📈 Nombre de comptes de charge: {count_value}"
                elif 'compte' in question_lower and 'actif' in question_lower:
                    return f"📈 Nombre de comptes d'actif: {count_value}"
                elif 'compte' in question_lower and 'passif' in question_lower:
                    return f"📈 Nombre de comptes de passif: {count_value}"
                elif 'compte' in question_lower:
                    return f"📈 Nombre total de comptes: {count_value}"
                elif 'écriture' in question_lower:
                    return f"📝 Nombre d'écritures: {count_value}"
                elif 'transaction' in question_lower:
                    return f"🔢 Nombre de transactions: {count_value}"
                else:
                    return f"📊 Nombre: {count_value}"
        
        elif result_type == "accounts":
            if len(data) == 1:
                account = first_row
                solde = account.get('solde', 'N/A')
                if solde != 'N/A':
                    return f"✅ Compte {account['numero']}: {account['intitule']} ({account.get('type', '')}) - Solde: {float(solde):,.2f} €"
                else:
                    return f"✅ Compte {account['numero']}: {account['intitule']} ({account.get('type', '')})"
            else:
                return f"📋 {len(data)} compte(s) trouvé(s)"
        
        elif result_type == "journal_entries":
            if len(data) == 1:
                entry = first_row
                col_name = 'numeroEcriture' if 'numeroEcriture' in entry else 'numeroecriture'
                return f"📝 Écriture {entry[col_name]} du {entry['date']}: {entry['libelle']}"
            else:
                return f"📝 {len(data)} écriture(s) trouvée(s)"
        
        # Fallback intelligent
        if len(data) == 1:
            # Si une seule ligne, montrer les valeurs principales
            main_values = []
            for key, value in first_row.items():
                if value and str(value).strip():
                    main_values.append(f"{key}: {value}")
            
            if main_values:
                return " | ".join(main_values[:3])
        
        return f"✅ {len(data)} résultat(s) trouvé(s)"

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '').strip()
            session_id = data.get('session_id', 'default_session')
            
            if not user_question:
                return JsonResponse({'error': 'La question est requise'}, status=400)
            
            print(f"📥 Question reçue: {user_question}")
            print(f"🔧 Statut Gemini: {'✅ Disponible' if self.gemini_available else '❌ Indisponible'}")
            
            # Réinitialiser Gemini si nécessaire
            if not self.gemini_available:
                print("🔄 Tentative de réinitialisation de Gemini...")
                self._initialize_gemini()
            
            # Gestion de la conversation
            user, created = User.objects.get_or_create(username='chatbot_user')
            conversation, created = ChatConversation.objects.get_or_create(
                session_id=session_id, defaults={'user': user}
            )
            
            ChatMessage.objects.create(
                conversation=conversation,
                message_type='USER',
                content=user_question
            )
            
            # Génération de la requête SQL
            sql_query = None
            gemini_used = False
            
            # Essayer Gemini d'abord
            if self.gemini_available:
                gemini_response = self.generate_sql_with_gemini(user_question)
                if gemini_response:
                    sql_query = self.extract_sql_from_response(gemini_response)
                    if sql_query:
                        gemini_used = True
                        print("✅ Requête générée par Gemini")
            
            # Fallback si Gemini échoue
            if not sql_query:
                sql_query = self.get_intelligent_fallback_query(user_question)
                print("🔄 Requête générée par le fallback")
            
            # Debug de la requête SQL
            if sql_query:
                print(f"🔍 REQUÊTE SQL AVANT EXÉCUTION: {sql_query}")
                if '""' in sql_query:
                    print("⚠️  ATTENTION: Guillemets doubles détectés dans la requête")
                    sql_query = sql_query.replace('""', '"')
                    print(f"🔧 REQUÊTE CORRIGÉE: {sql_query}")
            
            # Exécution de la requête
            response_data, sql_error = self.execute_safe_sql(sql_query)
            
            # Formatage de la réponse
            if sql_error:
                bot_response = f"❌ Erreur: {sql_error}"
            else:
                bot_response = self.format_response(response_data, user_question)
            
            print(f"📤 Réponse finale: {bot_response}")
            
            # Sauvegarde
            bot_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='BOT',
                content=bot_response,
                sql_query_used=sql_query,
                metadata={
                    'data_count': len(response_data) if response_data else 0,
                    'gemini_used': gemini_used,
                    'gemini_available': self.gemini_available,
                    'error': sql_error
                }
            )
            
            return JsonResponse({
                'response': bot_response,
                'session_id': session_id,
                'data_count': len(response_data) if response_data else 0,
                'has_data': bool(response_data and len(response_data) > 0),
                'gemini_used': gemini_used,
                'gemini_available': self.gemini_available,
                'timestamp': bot_message.timestamp.isoformat()
            })
            
        except Exception as e:
            print(f"💥 Erreur interne: {str(e)}")
            return JsonResponse({'error': f'Erreur interne: {str(e)}'}, status=500)


class GeminiStatusView(View):
    """Vue pour debugger l'état de Gemini"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        chatbot = AccountingChatBotView()
        basic_status = chatbot.get_gemini_status()
        
        return JsonResponse({
            'basic_status': basic_status,
            'message': 'Gemini est opérationnel avec toutes les requêtes professionnelles intégrées'
        })


class ChatHistoryView(View):
    """Vue pour récupérer l'historique des conversations"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, session_id):
        try:
            print(f"📖 Chargement historique pour session: {session_id}")
            
            # Récupérer la conversation
            conversation = ChatConversation.objects.get(session_id=session_id)
            messages = conversation.messages.all().order_by('timestamp')
            
            # Formater l'historique
            history = []
            for msg in messages:
                history.append({
                    'type': msg.message_type,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'sql_query': msg.sql_query_used,
                    'data_count': msg.metadata.get('data_count', 0) if msg.metadata else 0,
                    'gemini_used': msg.metadata.get('gemini_used', False) if msg.metadata else False
                })
            
            print(f"✅ Historique chargé: {len(history)} messages")
            
            return JsonResponse({
                'session_id': session_id,
                'history': history,
                'conversation_created': conversation.created_at.isoformat(),
                'message_count': len(history)
            })
            
        except ChatConversation.DoesNotExist:
            print(f"❌ Aucune conversation trouvée pour session: {session_id}")
            return JsonResponse({
                'history': [], 
                'session_id': session_id,
                'message_count': 0
            })
        except Exception as e:
            print(f"💥 Erreur chargement historique: {str(e)}")
            return JsonResponse({'error': f'Erreur chargement historique: {str(e)}'}, status=500)


class AccountingSummaryView(View):
    """Endpoint pour des résumés comptables prédéfinis"""
    
    def get(self, request):
        try:
            print("📊 Génération du résumé comptable")
            
            with connection.cursor() as cursor:
                # Total des débits et crédits
                cursor.execute("""
                    SELECT 
                        SUM(debit) as total_debit,
                        SUM(credit) as total_credit,
                        COUNT(*) as nombre_transactions
                    FROM accounting_transactionline
                """)
                totals = cursor.fetchone()
                total_debit = totals[0] or 0
                total_credit = totals[1] or 0
                nb_transactions = totals[2] or 0
                
                # Nombre d'écritures
                cursor.execute("SELECT COUNT(*) FROM accounting_journalentry")
                nb_ecritures = cursor.fetchone()[0] or 0
                
                # Nombre de comptes
                cursor.execute("SELECT COUNT(*) FROM accounting_account")
                nb_comptes = cursor.fetchone()[0] or 0
                
                # Dernières écritures
                cursor.execute("""
                    SELECT "numeroEcriture", date, libelle, reference 
                    FROM accounting_journalentry 
                    ORDER BY date DESC, id DESC 
                    LIMIT 5
                """)
                columns = [col[0] for col in cursor.description]
                recent_entries = [
                    dict(zip(columns, row)) for row in cursor.fetchall()
                ]
                
                # Comptes les plus utilisés
                cursor.execute("""
                    SELECT a.numero, a.intitule, COUNT(t.id) as usage_count
                    FROM accounting_account a
                    JOIN accounting_transactionline t ON a.id = t.account_id
                    GROUP BY a.id, a.numero, a.intitule
                    ORDER BY usage_count DESC
                    LIMIT 10
                """)
                columns = [col[0] for col in cursor.description]
                top_accounts = [
                    dict(zip(columns, row)) for row in cursor.fetchall()
                ]
            
            summary_data = {
                'summary': {
                    'total_debit': float(total_debit),
                    'total_credit': float(total_credit),
                    'nombre_transactions': nb_transactions,
                    'nombre_ecritures': nb_ecritures,
                    'nombre_comptes': nb_comptes,
                    'solde_global': float(total_debit - total_credit)
                },
                'recent_entries': recent_entries,
                'top_accounts': top_accounts
            }
            
            print(f"✅ Résumé généré: {nb_comptes} comptes, {nb_ecritures} écritures")
            return JsonResponse(summary_data)
            
        except Exception as e:
            print(f"💥 Erreur génération résumé: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)


class ConversationListView(View):
    """Vue pour lister toutes les conversations"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        try:
            print("📋 Chargement liste des conversations")
            
            # Récupérer les 20 dernières conversations
            conversations = ChatConversation.objects.all().order_by('-created_at')[:20]
            
            conversation_list = []
            for conv in conversations:
                # Récupérer le premier message utilisateur pour le titre
                first_user_message = conv.messages.filter(message_type='USER').first()
                title = first_user_message.content[:50] + '...' if first_user_message and len(first_user_message.content) > 50 else (
                    first_user_message.content if first_user_message else 'Nouvelle conversation'
                )
                
                # Compter les messages
                message_count = conv.messages.count()
                
                conversation_list.append({
                    'id': conv.id,
                    'session_id': conv.session_id,
                    'title': title,
                    'created_at': conv.created_at.isoformat(),
                    'updated_at': conv.updated_at.isoformat(),
                    'message_count': message_count
                })
            
            print(f"✅ Liste conversations chargée: {len(conversation_list)} conversations")
            
            return JsonResponse({
                'conversations': conversation_list,
                'total_count': len(conversation_list)
            })
            
        except Exception as e:
            print(f"💥 Erreur chargement liste conversations: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)