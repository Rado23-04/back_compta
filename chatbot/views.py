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
            
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                print("❌ Clé API Gemini non configurée")
                return
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            models_to_try = [
                'gemini-2.0-flash',
                'gemini-2.0-flash-001',
                'gemini-flash-latest',
                'gemini-2.0-flash-lite',
                'gemini-pro-latest',
            ]
            
            for model_name in models_to_try:
                try:
                    print(f"🔄 Test du modèle: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    test_response = self.model.generate_content("Réponds juste par 'OK'")
                    
                    if test_response and test_response.text:
                        self.gemini_available = True
                        print(f"✅ Gemini initialisé avec: {model_name}")
                        return
                        
                except Exception as e:
                    print(f"❌ {model_name} échoué: {str(e)[:100]}...")
                    continue
            
            self.gemini_available = False
                
        except Exception as e:
            print(f"💥 Erreur initialisation: {str(e)}")
            self.gemini_available = False

    # ==================== SYSTÈME DE DÉTECTION D'INTENTION ====================
    
    def detect_user_intent(self, user_question):
        """Détecte l'intention PRÉCISE de l'utilisateur avec scoring"""
        question_lower = user_question.lower()
        
        # Dictionnaire d'intentions avec motifs et scores
        intentions = {
            'EXACT_AMOUNT': {
                'patterns': [
                    r'combien (il y a|fait|coûte|vaut).*(solde|montant|total)',
                    r'quel est (le|la) (solde|montant|total)',
                    r'quelle est la (valeur|somme)',
                    r'montant (du|des)',
                    r'solde (du|des)',
                    r'chiffre (du|des)',
                    r'[0-9]{6}.*(solde|montant)'
                ],
                'keywords': ['combien', 'montant', 'solde exact', 'quel est le', 'quelle est la']
            },
            'EXACT_COUNT': {
                'patterns': [
                    r'combien de',
                    r'nombre de',
                    r'nombre total',
                    r'count',
                    r'combien (y a-t-il|existe)',
                    r'quantité de'
                ],
                'keywords': ['combien de', 'nombre de', 'combien existe', 'quantité']
            },
            'SPECIFIC_BALANCE': {
                'patterns': [
                    r'solde (des|du).*(créditeurs|fournisseurs)',
                    r'solde (des|du).*(débiteurs|clients)',
                    r'créditeurs.*solde',
                    r'débiteurs.*solde',
                    r'fournisseurs.*montant',
                    r'clients.*montant'
                ],
                'keywords': ['créditeurs', 'débiteurs', 'fournisseurs', 'clients']
            },
            'LIST_RECORDS': {
                'patterns': [
                    r'liste(r|z) (les|des)',
                    r'affiche(r|z) (les|des)',
                    r'montre(r|z) (les|des)',
                    r'voir (les|des)',
                    r'quels sont (les|des)'
                ],
                'keywords': ['liste', 'affiche', 'montre', 'voir les', 'quels sont']
            },
            'DETAILED_ANALYSIS': {
                'patterns': [
                    r'analyse(r|z)',
                    r'détaill(e|é)',
                    r'composition',
                    r'répartition',
                    r'ventilation'
                ],
                'keywords': ['analyse', 'détail', 'composition', 'répartition']
            },
            'COMPARISON': {
                'patterns': [
                    r'comparer',
                    r'comparaison',
                    r'vs',
                    r'par rapport',
                    r'évolution',
                    r'variation'
                ],
                'keywords': ['comparer', 'vs', 'évolution', 'variation']
            },
            'BALANCE_SHEET': {
                'patterns': [
                    r'bilan',
                    r'situation.*financière',
                    r'équilibre.*financier',
                    r'patrimoine'
                ],
                'keywords': ['bilan', 'situation financière', 'patrimoine']
            },
            'INCOME_STATEMENT': {
                'patterns': [
                    r'compte.*résultat',
                    r'résultat.*exercice',
                    r'bénéfice',
                    r'perte',
                    r'profit'
                ],
                'keywords': ['compte de résultat', 'résultat', 'bénéfice', 'perte']
            }
        }
        
        # Calcul du score pour chaque intention
        scores = {}
        for intent_name, intent_data in intentions.items():
            score = 0
            
            # Vérification des motifs regex
            for pattern in intent_data['patterns']:
                if re.search(pattern, question_lower):
                    score += 3
            
            # Vérification des mots-clés
            for keyword in intent_data['keywords']:
                if keyword in question_lower:
                    score += 2
        
            scores[intent_name] = score
        
        # Retourner l'intention avec le score le plus élevé
        best_intent = max(scores.items(), key=lambda x: x[1])
        
        # Seuil minimum de confiance
        if best_intent[1] >= 2:
            print(f"🎯 Intention détectée: {best_intent[0]} (score: {best_intent[1]})")
            return best_intent[0]
        else:
            print("🎯 Intention: GÉNÉRIQUE (score insuffisant)")
            return 'GENERIC'

    # ==================== SYSTÈME DE RÉPONSE INTENTIONNELLE ====================
    
    def generate_precise_response(self, user_question, sql_data, sql_query):
        """Génère une réponse EXACTE basée sur l'intention détectée"""
        intent = self.detect_user_intent(user_question)
        
        # Réponses spécifiques par intention
        response_handlers = {
            'EXACT_AMOUNT': self._handle_exact_amount,
            'EXACT_COUNT': self._handle_exact_count,
            'SPECIFIC_BALANCE': self._handle_specific_balance,
            'LIST_RECORDS': self._handle_list_records,
            'DETAILED_ANALYSIS': self._handle_detailed_analysis,
            'COMPARISON': self._handle_comparison,
            'BALANCE_SHEET': self._handle_balance_sheet,
            'INCOME_STATEMENT': self._handle_income_statement,
            'GENERIC': self._handle_generic
        }
        
        handler = response_handlers.get(intent, self._handle_generic)
        return handler(user_question, sql_data, sql_query)

    def _handle_exact_amount(self, user_question, data, sql_query):
        """Gère les demandes de montant EXACT"""
        if not data:
            return "❌ Aucun montant trouvé pour votre demande précise."
        
        # Extraire TOUS les montants numériques
        amounts = []
        for item in data:
            for key, value in item.items():
                if isinstance(value, (int, float)) and value != 0:
                    amounts.append({
                        'label': key.replace('_', ' ').title(),
                        'value': value,
                        'row': item
                    })
        
        if not amounts:
            return "ℹ️ Des données existent mais aucun montant numérique n'a été identifié."
        
        # Si un seul montant significatif, le retourner directement
        if len(amounts) == 1:
            amount = amounts[0]
            return f"💰 **{amount['label']} : {float(amount['value']):,.2f} €**"
        
        # Si plusieurs montants, trouver le plus pertinent
        question_lower = user_question.lower()
        
        # Priorité aux colonnes contenant des mots-clés de la question
        for amount in amounts:
            amount_label_lower = amount['label'].lower()
            if any(keyword in amount_label_lower for keyword in ['solde', 'total', 'montant', 'sum']):
                return f"💰 **{amount['label']} : {float(amount['value']):,.2f} €**"
        
        # Sinon, retourner le premier montant significatif
        primary_amount = amounts[0]
        return f"💰 **{primary_amount['label']} : {float(primary_amount['value']):,.2f} €**"

    def _handle_exact_count(self, user_question, data, sql_query):
        """Gère les demandes de comptage EXACT"""
        if not data:
            return "❌ Aucun élément à compter trouvé."
        
        # Chercher une colonne de comptage explicite
        if data and len(data) > 0:
            first_row = data[0]
            count_columns = [col for col in first_row.keys() 
                            if any(keyword in col.lower() for keyword in ['count', 'nombre', 'total', 'nb', 'number'])]
            
            if count_columns:
                count_value = first_row[count_columns[0]]
                return f"🔢 **{count_columns[0].replace('_', ' ').title()} : {int(count_value)}**"
        
        # Utiliser le nombre de lignes comme fallback
        return f"📊 **Nombre d'éléments trouvés : {len(data)}**"

    def _handle_specific_balance(self, user_question, data, sql_query):
        """Gère les soldes spécifiques (créditeurs, débiteurs, etc.)"""
        question_lower = user_question.lower()
        
        if 'créditeur' in question_lower or 'fournisseur' in question_lower:
            return self._get_creditors_balance_detailed(data)
        elif 'débiteur' in question_lower or 'client' in question_lower:
            return self._get_debtors_balance_detailed(data)
        else:
            return self._handle_exact_amount(user_question, data, sql_query)

    def _handle_list_records(self, user_question, data, sql_query):
        """Gère les demandes de liste"""
        if not data:
            return "❌ Aucun enregistrement à afficher."
        
        if len(data) <= 10:  # Afficher directement si peu d'éléments
            return self._format_record_list_detailed(data, user_question)
        else:
            return f"📋 **{len(data)} éléments trouvés**\n\n💡 *Pour voir le détail, précisez votre demande ou demandez moins de résultats.*"

    def _handle_detailed_analysis(self, user_question, data, sql_query):
        """Gère les demandes d'analyse détaillée"""
        if not data:
            return "❌ Aucune donnée pour l'analyse demandée."
        
        return self._generate_detailed_analysis(data, user_question)

    def _handle_comparison(self, user_question, data, sql_query):
        """Gère les demandes de comparaison"""
        if not data:
            return "❌ Données insuffisantes pour la comparaison."
        
        return self._generate_comparison_analysis(data, user_question)

    def _handle_balance_sheet(self, user_question, data, sql_query):
        """Gère les demandes de bilan"""
        return self.analyze_balance_sheet(data)

    def _handle_income_statement(self, user_question, data, sql_query):
        """Gère les demandes de compte de résultat"""
        return self.analyze_income_statement(data)

    def _handle_generic(self, user_question, data, sql_query):
        """Gère les demandes génériques avec intelligence"""
        if not data:
            return "🤔 Je n'ai pas trouvé de données correspondant à votre demande. Pouvez-vous la reformuler ?"
        
        # Analyser la structure des données pour deviner l'intention
        if len(data) == 1:
            return self._format_single_record(data[0])
        else:
            return self._smart_data_summary(data, user_question)

    # ==================== MÉTHODES DE SUPPORT AVANCÉES ====================

    def _get_creditors_balance_detailed(self, data):
        """Version améliorée pour les créditeurs"""
        if not data:
            return "❌ Aucun compte créditeur trouvé."
        
        total = 0
        details = []
        
        for item in data:
            solde = self._extract_numeric_value(item, 'solde')
            if solde > 0:
                total += solde
                compte_info = self._format_account_info(item)
                if compte_info:
                    details.append(f"{compte_info}: {solde:,.2f} €")
        
        if total == 0:
            return "ℹ️ Aucun solde créditeur significatif trouvé."
        
        response = f"💰 **SOLDE CRÉDITEURS TOTAL : {total:,.2f} €**\n\n"
        
        if details:
            response += "📋 **Détail des comptes :**\n"
            for detail in details[:8]:
                response += f"• {detail}\n"
            
            if len(details) > 8:
                response += f"\n... et {len(details) - 8} autres comptes"
        
        return response

    def _get_debtors_balance_detailed(self, data):
        """Version améliorée pour les débiteurs"""
        if not data:
            return "❌ Aucun compte débiteur trouvé."
        
        total = 0
        details = []
        
        for item in data:
            solde = self._extract_numeric_value(item, 'solde')
            if solde > 0:
                total += solde
                compte_info = self._format_account_info(item)
                if compte_info:
                    details.append(f"{compte_info}: {solde:,.2f} €")
        
        if total == 0:
            return "ℹ️ Aucun solde débiteur significatif trouvé."
        
        response = f"💰 **SOLDE DÉBITEURS TOTAL : {total:,.2f} €**\n\n"
        
        if details:
            response += "📋 **Détail des comptes :**\n"
            for detail in details[:8]:
                response += f"• {detail}\n"
            
            if len(details) > 8:
                response += f"\n... et {len(details) - 8} autres comptes"
        
        return response

    def _format_single_record(self, record):
        """Formate un enregistrement unique de manière intelligente"""
        key_info = []
        
        for key, value in record.items():
            if value is not None and key not in ['id', 'journal_entry_id', 'account_id']:
                formatted_key = key.replace('_', ' ').title()
                
                if isinstance(value, (int, float)) and value != 0:
                    formatted_value = f"{float(value):,.2f} €"
                elif isinstance(value, str) and value.strip():
                    formatted_value = value
                elif isinstance(value, datetime):
                    formatted_value = value.strftime('%d/%m/%Y')
                else:
                    continue
                    
                key_info.append(f"**{formatted_key}** : {formatted_value}")
        
        if key_info:
            return "✅ **Résultat trouvé :**\n" + "\n".join(key_info[:6])
        else:
            return "ℹ️ Données trouvées mais format non reconnu."

    def _format_record_list_detailed(self, data, user_question):
        """Formate une liste d'enregistrements de manière détaillée"""
        if not data:
            return "Aucune donnée à afficher."
        
        response = f"📋 **{len(data)} éléments trouvés :**\n\n"
        
        for i, item in enumerate(data[:10], 1):  # Limiter à 10 éléments
            response += f"**{i}. {self._format_item_summary(item)}**\n"
        
        if len(data) > 10:
            response += f"\n... et {len(data) - 10} autres éléments"
        
        return response

    def _format_item_summary(self, item):
        """Résumé intelligent d'un élément"""
        if 'numero' in item and 'intitule' in item:
            base = f"{item['numero']} - {item['intitule']}"
            if 'solde' in item:
                solde = self._extract_numeric_value(item, 'solde')
                return f"{base} : {solde:,.2f} €"
            return base
        elif 'numeroEcriture' in item and 'libelle' in item:
            return f"{item['numeroEcriture']} - {item['libelle']}"
        else:
            # Fallback générique
            key_values = []
            for key, value in list(item.items())[:3]:  # Premières 3 colonnes
                if key not in ['id'] and value:
                    key_values.append(f"{value}")
            return " | ".join(key_values)

    def _smart_data_summary(self, data, user_question):
        """Résumé intelligent des données multiples"""
        if not data:
            return "Aucune donnée à résumer."
        
        total_records = len(data)
        first_record = data[0]
        
        # Si ce sont des comptes avec soldes
        if 'solde' in first_record:
            soldes = [self._extract_numeric_value(item, 'solde') for item in data]
            solde_total = sum(soldes)
            solde_moyen = solde_total / len(soldes) if soldes else 0
            
            return f"""📊 **Analyse des {total_records} comptes trouvés :**

• **Solde total** : {solde_total:,.2f} €
• **Solde moyen** : {solde_moyen:,.2f} €
• **Fourchette** : {min(soldes):,.2f} € à {max(soldes):,.2f} €

💡 *Pour plus de détails, précisez votre demande ou demandez un compte spécifique.*"""
        
        # Si ce sont des écritures
        elif any(key in first_record for key in ['numeroEcriture', 'numeroecriture']):
            return f"""📝 **{total_records} écritures trouvées**

💡 *Demandez "détail des écritures" pour voir le contenu ou précisez une période/critère.*"""
        
        # Résumé générique
        return f"""✅ **{total_records} résultats trouvés**

💡 *Pour une réponse plus précise, vous pouvez :*
• Demander un montant spécifique ("combien", "montant")
• Demander le détail ("liste", "affiche")
• Précisez un critère de recherche"""

    def _generate_detailed_analysis(self, data, user_question):
        """Génère une analyse détaillée des données"""
        if not data:
            return "Aucune donnée à analyser."
        
        analysis = f"📊 **ANALYSE DÉTAILLÉE**\n\n"
        analysis += f"• **Nombre total d'éléments** : {len(data)}\n"
        
        # Statistiques de base
        if data and len(data) > 0:
            first_item = data[0]
            numeric_columns = [k for k, v in first_item.items() if isinstance(v, (int, float)) and v != 0]
            
            if numeric_columns:
                analysis += f"• **Colonnes numériques** : {', '.join(numeric_columns[:3])}\n"
            
            # Exemple de premiers éléments
            analysis += f"\n**Exemples :**\n"
            for i, item in enumerate(data[:3], 1):
                analysis += f"{i}. {self._format_item_summary(item)}\n"
        
        return analysis

    def _generate_comparison_analysis(self, data, user_question):
        """Génère une analyse comparative"""
        if len(data) < 2:
            return "❌ Données insuffisantes pour une comparaison significative."
        
        comparison = f"📈 **ANALYSE COMPARATIVE**\n\n"
        
        # Simple comparaison si données numériques
        if 'solde' in data[0]:
            soldes = [self._extract_numeric_value(item, 'solde') for item in data]
            comparison += f"• **Écart entre min et max** : {max(soldes) - min(soldes):,.2f} €\n"
            comparison += f"• **Ratio max/min** : {max(soldes)/min(soldes) if min(soldes) != 0 else 'N/A':.2f}\n"
        
        return comparison

    def _extract_numeric_value(self, item, key):
        """Extrait une valeur numérique de manière sécurisée"""
        value = item.get(key, 0)
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value) if value else 0
        except (TypeError, ValueError):
            return 0

    def _format_account_info(self, item):
        """Formate les informations de compte"""
        parts = []
        if 'numero' in item:
            parts.append(item['numero'])
        if 'intitule' in item:
            parts.append(item['intitule'])
        return ' - '.join(parts) if parts else None

    # ==================== MÉTHODES D'ANALYSE EXISTANTES AMÉLIORÉES ====================

    def analyze_balance_sheet(self, data):
        """Analyse conversationnelle du bilan"""
        actif = next((item for item in data if item.get('type') == 'Actif'), {})
        passif = next((item for item in data if item.get('type') == 'Passif'), {})
        
        solde_actif = actif.get('solde', 0) or actif.get('total_debit', 0) or 0
        solde_passif = passif.get('solde', 0) or passif.get('total_credit', 0) or 0
        
        response = "📊 **ANALYSE DE VOTRE BILAN**\n\n"
        response += f"• **Actif total**: {float(solde_actif):,.2f} €\n"
        response += f"• **Passif total**: {float(solde_passif):,.2f} €\n"
        
        # Analyse d'équilibre
        if abs(solde_actif - solde_passif) < 0.01:
            response += "• **Équilibre**: ✅ Bilan parfaitement équilibré\n"
        else:
            ecart = abs(solde_actif - solde_passif)
            response += f"• **Écart**: ⚠️ Différence de {float(ecart):,.2f} €\n"
        
        # Conseils
        response += "\n💡 **CONSEILS**:\n"
        if solde_actif > 500000:
            response += "• Structure patrimoniale importante\n"
        if solde_passif / solde_actif < 0.5:
            response += "• Excellente autonomie financière\n"
        
        response += "\nSouhaitez-vous une analyse détaillée par poste ?"
        
        return response

    def analyze_income_statement(self, data):
        """Analyse conversationnelle du compte de résultat"""
        charges = next((item for item in data if item.get('type') == 'Charge'), {})
        produits = next((item for item in data if item.get('type') == 'Produit'), {})
        
        total_charges = charges.get('charges', 0) or charges.get('total_debit', 0) or 0
        total_produits = produits.get('produits', 0) or produits.get('total_credit', 0) or 0
        resultat = total_produits - total_charges
        
        response = "📈 **COMPTE DE RÉSULTAT**\n\n"
        response += f"• **Produits totaux**: {float(total_produits):,.2f} €\n"
        response += f"• **Charges totales**: {float(total_charges):,.2f} €\n"
        response += f"• **Résultat**: {'💰' if resultat >= 0 else '🔴'} **{float(resultat):,.2f} €** "
        response += f"({'Bénéfice' if resultat >= 0 else 'Perte'})\n"
        
        if total_produits > 0:
            marge = (resultat / total_produits) * 100
            response += f"• **Marge nette**: {marge:.1f}%\n"
        
        # Interprétation
        if resultat > 0:
            response += "\n🎯 **Performance**: Rentabilité positive - excellente santé financière"
        else:
            response += "\n🎯 **Performance**: Résultat négatif - analysez vos charges"
        
        return response

    # ==================== MÉTHODES GEMINI EXISTANTES ====================

    def generate_conversational_response(self, user_question, sql_data=None, sql_query=None):
        """Génère des réponses conversationnelles naturelles comme Gemini"""
        if not self.gemini_available or not self.model:
            return self.generate_precise_response(user_question, sql_data, sql_query)
        
        try:
            # Construire le contexte basé sur les données
            data_context = ""
            if sql_data and len(sql_data) > 0:
                data_summary = self._generate_data_summary_for_ai(sql_data)
                data_context = f"""
                DONNÉES ANALYSÉES:
                {data_summary}
                """
            
            prompt = f"""
            Tu es un expert comptable français assistant IA. Ton style est conversationnel, naturel et professionnel.

            QUESTION: "{user_question}"

            {data_context}

            Fournis une réponse PRÉCISE, UTILE et CONVERSATIONNELLE. Réponds exactement à ce qui est demandé.

            Ta réponse:
            """
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1500,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            if response.text:
                return response.text
            else:
                return self.generate_precise_response(user_question, sql_data, sql_query)
                
        except Exception as e:
            print(f"💥 Erreur génération réponse: {str(e)}")
            return self.generate_precise_response(user_question, sql_data, sql_query)

    def _generate_data_summary_for_ai(self, data):
        """Résume les données pour l'IA"""
        if not data or len(data) == 0:
            return "Aucune donnée trouvée"
        
        summary = f"Nombre d'enregistrements: {len(data)}\n"
        
        if len(data) > 0:
            first_row = data[0]
            key_columns = [k for k in first_row.keys() if k not in ['id', 'journal_entry_id', 'account_id']]
            
            summary += "Colonnes principales: " + ", ".join(key_columns[:5]) + "\n"
            
            # Ajouter des exemples de valeurs
            if len(data) <= 3:
                summary += "\nDonnées:\n"
                for i, item in enumerate(data):
                    summary += f"{i+1}. {self._format_item_summary(item)}\n"
        
        return summary

    def generate_sql_with_gemini(self, user_question):
        """Génération SQL avec Gemini"""
        if not self.gemini_available or not self.model:
            return None
        
        try:
            prompt = f"""
            Tu es un expert SQL et comptable français. Génère UNIQUEMENT une requête SQL PostgreSQL.

            QUESTION: "{user_question}"

            STRUCTURE:
            - accounting_account (id, numero, intitule, classe, type, "soldeInitial")
            - accounting_journalentry (id, date, libelle, reference, "numeroEcriture")
            - accounting_transactionline (id, journal_entry_id, account_id, debit, credit)

            RÈGLES:
            1. UNIQUEMENT SELECT
            2. Tables exactes: accounting_account, accounting_journalentry, accounting_transactionline
            3. Guillemets pour: "numeroEcriture", "soldeInitial"
            4. Formate: ```sql [requête] ```

            REQUÊTE POUR: "{user_question}"
            """
            
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            if response.text:
                return response.text
            return None
                
        except Exception as e:
            print(f"💥 Erreur génération SQL: {str(e)}")
            return None

    def get_universal_fallback_query(self, user_question):
        """Fallback intelligent universel"""
        question_lower = user_question.lower()
        
        # Détection avancée par motifs
        patterns = {
            r'solde.*compte.*(\d{6})': lambda m: f"""
                SELECT a.numero, a.intitule, 
                       COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde
                FROM accounting_account a
                LEFT JOIN accounting_transactionline t ON a.id = t.account_id
                WHERE a.numero = '{m.group(1)}'
                GROUP BY a.id, a.numero, a.intitule;
            """,
            r'total.*débit': "SELECT SUM(debit) as total_debits FROM accounting_transactionline;",
            r'dernières.*écritures': "SELECT \"numeroEcriture\", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 10;",
        }
        
        for pattern, query in patterns.items():
            match = re.search(pattern, question_lower)
            if match:
                return query(match).strip() if callable(query) else query.strip()
        
        # Fallback par défaut
        return "SELECT COUNT(*) as total_comptes FROM accounting_account;"

    def extract_sql_from_response(self, text):
        """Extrait le SQL de la réponse Gemini"""
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
                sql = sql.replace('```sql', '').replace('```', '').strip()
                sql = sql.replace('""', '"')
                return sql
        
        return None

    def execute_safe_sql(self, sql_query):
        """Exécute le SQL de manière sécurisée"""
        try:
            if not sql_query:
                return None, "Requête SQL vide"
            
            sql_query = sql_query.strip()
            sql_query = sql_query.replace('""soldeInitial""', '"soldeInitial"')
            sql_query = sql_query.replace('""numeroEcriture""', '"numeroEcriture"')
            
            # Vérification de sécurité
            dangerous_keywords = ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            sql_upper = sql_query.upper()
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return None, f"Requête non autorisée: {keyword}"
            
            if not sql_upper.startswith('SELECT'):
                return None, "Seules les requêtes SELECT sont autorisées"
            
            print(f"🔍 Exécution SQL: {sql_query[:200]}...")
            
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
            return None, error_msg

    # ==================== MÉTHODE PRINCIPALE MISE À JOUR ====================

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
            
            print(f"📥 Question: {user_question}")
            print(f"🔧 Statut Gemini: {'✅ Disponible' if self.gemini_available else '❌ Indisponible'}")
            
            # Réinitialisation si nécessaire
            if not self.gemini_available:
                self._initialize_gemini()
            
            # Gestion conversation
            user, created = User.objects.get_or_create(username='chatbot_user')
            conversation, created = ChatConversation.objects.get_or_create(
                session_id=session_id, defaults={'user': user}
            )
            
            ChatMessage.objects.create(
                conversation=conversation,
                message_type='USER',
                content=user_question
            )
            
            # Génération SQL
            sql_query = None
            gemini_used = False
            
            if self.gemini_available:
                gemini_response = self.generate_sql_with_gemini(user_question)
                if gemini_response:
                    sql_query = self.extract_sql_from_response(gemini_response)
                    if sql_query:
                        gemini_used = True
                        print("✅ Requête générée par Gemini")
            
            if not sql_query:
                sql_query = self.get_universal_fallback_query(user_question)
                print("🔄 Requête par fallback")
            
            # Nettoyage SQL
            if sql_query:
                sql_query = sql_query.replace('""', '"').strip()
            
            # Exécution
            response_data, sql_error = self.execute_safe_sql(sql_query)
            
            # ✅ NOUVELLE MÉTHODE DE RÉPONSE INTELLIGENTE
            if sql_error:
                bot_response = "❌ Difficulté technique avec cette requête. Reformulez votre question."
            else:
                if self.gemini_available:
                    # Essayer d'abord la réponse conversationnelle
                    conversational_response = self.generate_conversational_response(user_question, response_data, sql_query)
                    if conversational_response and len(conversational_response) > 30:
                        bot_response = conversational_response
                    else:
                        # Fallback sur le système intentionnel
                        bot_response = self.generate_precise_response(user_question, response_data, sql_query)
                else:
                    # Système intentionnel direct
                    bot_response = self.generate_precise_response(user_question, response_data, sql_query)
            
            print(f"📤 Réponse générée")
            
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
            print(f"💥 Erreur: {str(e)}")
            return JsonResponse({
                'error': 'Problème technique. Réessayez.'
            }, status=500)

# ==================== CLASSES SUPPLEMENTAIRES ====================

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
            'message': 'Système comptable IA opérationnel'
        })

class ChatHistoryView(View):
    """Vue pour récupérer l'historique des conversations"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, session_id):
        try:
            print(f"📖 Chargement historique pour session: {session_id}")
            
            conversation = ChatConversation.objects.get(session_id=session_id)
            messages = conversation.messages.all().order_by('timestamp')
            
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
            return JsonResponse({'history': [], 'session_id': session_id, 'message_count': 0})
        except Exception as e:
            return JsonResponse({'error': f'Erreur chargement historique: {str(e)}'}, status=500)

class AccountingSummaryView(View):
    """Endpoint pour des résumés comptables prédéfinis"""
    
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT SUM(debit) as total_debit, SUM(credit) as total_credit FROM accounting_transactionline")
                totals = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) FROM accounting_journalentry")
                nb_ecritures = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM accounting_account")
                nb_comptes = cursor.fetchone()[0] or 0
            
            summary_data = {
                'summary': {
                    'total_debit': float(totals[0] or 0),
                    'total_credit': float(totals[1] or 0),
                    'nombre_ecritures': nb_ecritures,
                    'nombre_comptes': nb_comptes,
                }
            }
            
            return JsonResponse(summary_data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class ConversationListView(View):
    """Vue pour lister toutes les conversations"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        try:
            conversations = ChatConversation.objects.all().order_by('-created_at')[:20]
            
            conversation_list = []
            for conv in conversations:
                first_user_message = conv.messages.filter(message_type='USER').first()
                title = first_user_message.content[:50] + '...' if first_user_message and len(first_user_message.content) > 50 else (
                    first_user_message.content if first_user_message else 'Nouvelle conversation'
                )
                
                conversation_list.append({
                    'id': conv.id,
                    'session_id': conv.session_id,
                    'title': title,
                    'created_at': conv.created_at.isoformat(),
                    'updated_at': conv.updated_at.isoformat(),
                    'message_count': conv.messages.count()
                })
            
            return JsonResponse({'conversations': conversation_list})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)