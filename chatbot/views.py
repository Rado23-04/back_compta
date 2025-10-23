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
        """Initialise Gemini avec plusieurs modèles et gestion d'erreur complète"""
        try:
            # Vérifier que la clé API est configurée
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                print("❌ Clé API Gemini non configurée dans settings.py")
                return
            
            # Configurer Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Liste des modèles à essayer (du plus récent au plus ancien)
            models_to_try = [
                'gemini-1.5-flash',
                'gemini-1.5-flash-8b', 
                'gemini-1.5-pro',
                'gemini-1.0-pro',
                'gemini-pro'
            ]
            
            for model_name in models_to_try:
                try:
                    print(f"🔄 Tentative d'initialisation du modèle: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    
                    # Test avec une requête simple
                    test_response = self.model.generate_content("Réponds juste par 'OK'")
                    
                    if test_response.text:
                        self.gemini_available = True
                        print(f"✅ Gemini initialisé avec succès - Modèle: {model_name}")
                        print(f"✅ Test réponse: {test_response.text}")
                        return
                    
                except Exception as model_error:
                    print(f"❌ Modèle {model_name} non disponible: {str(model_error)}")
                    continue
            
            # Si aucun modèle ne fonctionne
            print("❌ Aucun modèle Gemini n'est disponible")
            self.model = None
            self.gemini_available = False
            
        except Exception as e:
            print(f"💥 Erreur critique d'initialisation Gemini: {str(e)}")
            self.model = None
            self.gemini_available = False

    def generate_sql_with_gemini(self, user_question):
        """Utilise Gemini pour générer une requête SQL avec un prompt optimisé"""
        if not self.gemini_available or not self.model:
            print("❌ Gemini non disponible pour cette requête")
            return None
        
        try:
            # Prompt optimisé pour la comptabilité
            prompt = f"""
            Tu es un expert SQL et comptable français. Génère UNIQUEMENT une requête SQL PostgreSQL pour répondre à cette question comptable.

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
            - "numeroEcriture" (VARCHAR(50)) - numéro d'écriture (NOTE: utiliser des guillemets)
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

            ### EXEMPLES DE REQUÊTES CORRECTES:

            Question: "Quel est le solde du compte 411000 ?"
            Réponse: ```sql SELECT a.numero, a.intitule, COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.credit), 0) as solde FROM accounting_account a LEFT JOIN accounting_transactionline t ON a.id = t.account_id WHERE a.numero = '411000' GROUP BY a.id, a.numero, a.intitule; ```

            Question: "Combien y a-t-il de comptes de charge ?"
            Réponse: ```sql SELECT COUNT(*) as nombre_comptes FROM accounting_account WHERE type = 'Charge'; ```

            Question: "Liste les 5 dernières écritures"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle FROM accounting_journalentry ORDER BY date DESC LIMIT 5; ```

            Question: "Total des débits du mois dernier"
            Réponse: ```sql SELECT SUM(debit) as total_debits FROM accounting_transactionline t JOIN accounting_journalentry j ON t.journal_entry_id = j.id WHERE j.date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND j.date < DATE_TRUNC('month', CURRENT_DATE); ```

            Question: "Trouve les écritures avec le libellé 'Client Dupont'"
            Réponse: ```sql SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry WHERE libelle ILIKE '%Client Dupont%' ORDER BY date DESC; ```

            MAINTENANT, GÉNÈRE LA REQUÊTE SQL POUR CETTE QUESTION:
            """

            print(f"🧠 Envoi à Gemini: {user_question}")
            
            # Configuration de la génération pour plus de stabilité
            generation_config = {
                "temperature": 0.1,  # Plus déterministe
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
            'écriture': 'SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 10;',
            'journal': 'SELECT "numeroEcriture", date, libelle, reference FROM accounting_journalentry ORDER BY date DESC LIMIT 10;',
            'compte': "SELECT numero, intitule, type, classe FROM accounting_account ORDER BY numero LIMIT 20;",
            'account': "SELECT numero, intitule, type, classe FROM accounting_account ORDER BY numero LIMIT 20;"
        }
        
        for keyword, query in keyword_queries.items():
            if keyword in question_lower:
                return query
        
        # Fallback par défaut
        return "SELECT COUNT(*) as total_comptes FROM accounting_account;"

    def extract_sql_from_response(self, text):
        """Extrait la requête SQL de la réponse"""
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
                print(f"✅ SQL extrait: {sql}")
                return sql
        
        return None

    def execute_safe_sql(self, sql_query):
        """Exécute une requête SQL de manière sécurisée"""
        try:
            if not sql_query:
                return None, "Requête SQL vide"
            
            # Nettoyer et corriger la requête
            sql_query = sql_query.strip()
            sql_query = sql_query.replace('numeroEcriture', '"numeroEcriture"')
            sql_query = sql_query.replace('soldeInitial', '"soldeInitial"')
            
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
            return None, error_msg

    def format_response(self, data, user_question):
        """Formate une réponse contextuelle"""
        if not data:
            return f"❌ Aucune donnée trouvée pour: '{user_question}'"
        
        question_lower = user_question.lower()
        
        # Réponses spécifiques basées sur le type de données
        if data and len(data) > 0:
            first_row = data[0]
            
            # Solde de compte
            if 'solde' in first_row and 'numero' in first_row:
                solde = first_row['solde'] or 0
                return f"💰 Solde du compte {first_row['numero']} ({first_row.get('intitule', '')}): {float(solde):,.2f} €"
            
            # Totaux
            if 'total_debit' in first_row:
                total = first_row['total_debit'] or 0
                return f"📊 Total des débits: {float(total):,.2f} €"
            
            if 'total_credit' in first_row:
                total = first_row['total_credit'] or 0
                return f"📊 Total des crédits: {float(total):,.2f} €"
            
            if 'nombre_comptes' in first_row:
                count = first_row['nombre_comptes']
                return f"📈 Nombre de comptes: {count}"
            
            # Comptes
            if 'numero' in first_row:
                if len(data) == 1:
                    return f"✅ Compte {first_row['numero']}: {first_row['intitule']} ({first_row.get('type', '')})"
                else:
                    return f"📋 {len(data)} compte(s) trouvé(s)"
            
            # Écritures
            if 'numeroecriture' in first_row or 'numeroEcriture' in first_row:
                if len(data) == 1:
                    col_name = 'numeroEcriture' if 'numeroEcriture' in first_row else 'numeroecriture'
                    return f"📝 Écriture {first_row[col_name]} du {first_row['date']}: {first_row['libelle']}"
                else:
                    return f"📝 {len(data)} écriture(s) trouvée(s)"
        
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