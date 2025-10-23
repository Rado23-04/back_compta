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

# Configuration Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class AccountingChatBotView(View):
    
    def __init__(self):
        super().__init__()
        self.model = genai.GenerativeModel('gemini-pro')
    
    def extract_sql_from_response(self, text):
        """Extrait la requête SQL de la réponse de Gemini avec plusieurs patterns"""
        if not text:
            return None
            
        print(f"🔍 Texte à analyser: {text}")
        
        # Pattern 1: Code block avec ```sql
        sql_pattern = r"```sql\s*(.*?)\s*```"
        matches = re.findall(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            print(f"✅ SQL trouvé avec pattern 1: {matches[0].strip()}")
            return matches[0].strip()
        
        # Pattern 2: Code block simple avec ```
        sql_pattern2 = r"```\s*(SELECT.*?)\s*```"
        matches2 = re.findall(sql_pattern2, text, re.DOTALL | re.IGNORECASE)
        if matches2:
            print(f"✅ SQL trouvé avec pattern 2: {matches2[0].strip()}")
            return matches2[0].strip()
        
        # Pattern 3: Requête SQL directe
        sql_pattern3 = r"(SELECT\s+.*?;)"
        matches3 = re.findall(sql_pattern3, text, re.DOTALL | re.IGNORECASE)
        if matches3:
            print(f"✅ SQL trouvé avec pattern 3: {matches3[0].strip()}")
            return matches3[0].strip()
        
        print("❌ Aucun SQL trouvé dans la réponse")
        return None
    
    def execute_safe_sql(self, sql_query):
        """Exécute une requête SQL de manière sécurisée"""
        try:
            dangerous_keywords = ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
            sql_upper = sql_query.upper().strip()
            
            print(f"🔍 Vérification sécurité SQL: {sql_query}")
            
            # Vérifier les mots-clés dangereux
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return None, f"Requête non autorisée: {keyword}"
            
            # Vérifier que c'est bien un SELECT
            if not sql_upper.startswith('SELECT'):
                return None, "Seules les requêtes SELECT sont autorisées"
            
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
                            elif hasattr(value, '__dict__'):
                                value = str(value)
                            row_data[col] = value
                        data.append(row_data)
                    
                    print(f"✅ Données récupérées: {len(data)} lignes")
                    return data, None
                else:
                    return [], "Requête exécutée mais aucun résultat retourné"
                
        except Exception as e:
            print(f"❌ Erreur SQL: {str(e)}")
            return None, f"Erreur SQL: {str(e)}"
    
    def generate_sql_query(self, user_question):
        """Utilise Gemini pour générer une requête SQL basée sur la question"""
        
        prompt = f"""
        Tu es un expert SQL spécialisé en comptabilité. Génère UNIQUEMENT une requête SQL PostgreSQL pour répondre à cette question.

        QUESTION: "{user_question}"

        STRUCTURE DE LA BASE DE DONNÉES COMPTABLE:

        Table: accounting_account
        - id (INTEGER, clé primaire)
        - numero (VARCHAR) - numéro du compte (ex: '411000')
        - intitule (VARCHAR) - intitulé du compte
        - classe (INTEGER) - classe comptable (1 à 8)
        - type (VARCHAR) - 'Actif', 'Passif', 'Charge', 'Produit', 'TVA', 'Autre'
        - nature (VARCHAR) - nature du compte
        - soldeInitial (DECIMAL) - solde initial

        Table: accounting_journalentry  
        - id (INTEGER, clé primaire)
        - date (DATE) - date de l'écriture
        - libelle (VARCHAR) - libellé de l'opération
        - numeroEcriture (VARCHAR) - numéro d'écriture
        - reference (VARCHAR) - référence

        Table: accounting_transactionline
        - id (INTEGER, clé primaire)
        - journal_entry_id (INTEGER) - clé étrangère vers accounting_journalentry
        - account_id (INTEGER) - clé étrangère vers accounting_account
        - debit (DECIMAL) - montant débit
        - credit (DECIMAL) - montant crédit
        - accountNumber (VARCHAR) - numéro de compte
        - accountName (VARCHAR) - nom du compte

        IMPORTANT: 
        1. Utilise UNIQUEMENT des requêtes SELECT
        2. Les noms de tables sont: accounting_account, accounting_journalentry, accounting_transactionline
        3. Formate la réponse avec la requête SQL entre ```sql et ```
        4. Sois précis dans les conditions WHERE
        5. Utilise des fonctions d'agrégation quand nécessaire (SUM, COUNT, AVG)

        Exemples de requêtes correctes:
        - "Combien de comptes ?" → ```sql SELECT COUNT(*) FROM accounting_account; ```
        - "Total des débits" → ```sql SELECT SUM(debit) FROM accounting_transactionline; ```
        - "Liste des comptes" → ```sql SELECT numero, intitule FROM accounting_account ORDER BY numero; ```
        - "Dernières écritures" → ```sql SELECT numeroEcriture, date, libelle FROM accounting_journalentry ORDER BY date DESC LIMIT 5; ```

        Réponds UNIQUEMENT avec la requête SQL formatée.
        """
        
        try:
            response = self.model.generate_content(prompt)
            print(f"🔍 Réponse Gemini brute: {response.text}")
            return response.text
        except Exception as e:
            print(f"❌ Erreur Gemini: {str(e)}")
            return None
    
    def get_fallback_query(self, user_question):
        """Requêtes de fallback pour les questions courantes"""
        question_lower = user_question.lower()
        
        fallback_queries = {
            'compte': "SELECT COUNT(*) as total_comptes FROM accounting_account;",
            'compter compte': "SELECT COUNT(*) as total_comptes FROM accounting_account;",
            'nombre compte': "SELECT COUNT(*) as total_comptes FROM accounting_account;",
            'combien compte': "SELECT COUNT(*) as total_comptes FROM accounting_account;",
            'total débit': "SELECT SUM(debit) as total_debit FROM accounting_transactionline;",
            'total crédit': "SELECT SUM(credit) as total_credit FROM accounting_transactionline;",
            'débit': "SELECT SUM(debit) as total_debit FROM accounting_transactionline;",
            'crédit': "SELECT SUM(credit) as total_credit FROM accounting_transactionline;",
            'écriture': "SELECT numeroEcriture, date, libelle FROM accounting_journalentry ORDER BY date DESC LIMIT 10;",
            'dernière écriture': "SELECT numeroEcriture, date, libelle FROM accounting_journalentry ORDER BY date DESC LIMIT 5;",
            'liste compte': "SELECT numero, intitule, type FROM accounting_account ORDER BY numero;",
            'classe 6': "SELECT numero, intitule FROM accounting_account WHERE classe = 6;",
            'charge': "SELECT numero, intitule FROM accounting_account WHERE type = 'Charge';",
            'produit': "SELECT numero, intitule FROM accounting_account WHERE type = 'Produit';",
            'actif': "SELECT numero, intitule FROM accounting_account WHERE type = 'Actif';",
            'passif': "SELECT numero, intitule FROM accounting_account WHERE type = 'Passif';"
        }
        
        for key, query in fallback_queries.items():
            if key in question_lower:
                print(f"🔄 Utilisation du fallback pour: {key}")
                return query
                
        return "SELECT COUNT(*) as total_comptes FROM accounting_account;"
    
    def format_data_response(self, data, user_question, sql_query=None):
        """Formate les données pour une réponse naturelle"""
        
        if not data:
            return f"Je n'ai trouvé aucune donnée correspondant à votre question : '{user_question}'. Pouvez-vous la reformuler ?"
        
        try:
            # Réponse simple basée sur les données
            if data and len(data) > 0:
                first_row = data[0]
                
                if 'total_debit' in first_row:
                    total = first_row['total_debit'] or 0
                    return f"Le total des débits est de {float(total):,.2f} €."
                
                elif 'total_credit' in first_row:
                    total = first_row['total_credit'] or 0
                    return f"Le total des crédits est de {float(total):,.2f} €."
                
                elif 'total_comptes' in first_row:
                    count = first_row['total_comptes']
                    return f"Il y a {count} comptes dans la base de données."
                
                elif 'numero' in first_row and 'intitule' in first_row:
                    if len(data) == 1:
                        return f"Compte {first_row['numero']} - {first_row['intitule']}"
                    else:
                        return f"J'ai trouvé {len(data)} comptes correspondant à votre recherche."
                
                elif 'numeroecriture' in first_row:
                    if len(data) == 1:
                        return f"Écriture {first_row['numeroecriture']} du {first_row['date']} : {first_row['libelle']}"
                    else:
                        return f"Voici les {len(data)} dernières écritures."
                
                else:
                    return f"J'ai trouvé {len(data)} enregistrement(s) correspondant à votre demande."
            
            return "Aucune donnée trouvée pour votre requête."
            
        except Exception as e:
            print(f"❌ Erreur formatage: {str(e)}")
            return f"J'ai trouvé {len(data)} enregistrement(s) correspondant à votre demande."
    
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
            
            # Récupérer ou créer la conversation
            user, created = User.objects.get_or_create(
                username='chatbot_user', 
                defaults={'email': 'chatbot@example.com'}
            )
            conversation, created = ChatConversation.objects.get_or_create(
                session_id=session_id,
                defaults={'user': user}
            )
            
            # Sauvegarder le message utilisateur
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='USER',
                content=user_question
            )
            
            # Générer la requête SQL avec Gemini
            gemini_sql_response = self.generate_sql_query(user_question)
            sql_query = self.extract_sql_from_response(gemini_sql_response)
            
            # Fallback si Gemini échoue
            if not sql_query:
                print("🔄 Utilisation du fallback")
                sql_query = self.get_fallback_query(user_question)
            
            print(f"🔍 Requête SQL générée: {sql_query}")
            
            response_data = None
            sql_error = None
            
            if sql_query:
                response_data, sql_error = self.execute_safe_sql(sql_query)
                print(f"📊 Données récupérées: {len(response_data) if response_data else 0} lignes")
                if sql_error:
                    print(f"❌ Erreur SQL: {sql_error}")
            else:
                sql_error = "Impossible de générer une requête SQL"
            
            if sql_error:
                bot_response = f"Je n'ai pas pu récupérer les données: {sql_error}. Pouvez-vous reformuler votre question ?"
                response_data = []  # Assure que data_count sera 0
            else:
                bot_response = self.format_data_response(response_data, user_question, sql_query)
            
            print(f"📤 Réponse du bot: {bot_response}")
            
            # Sauvegarder la réponse du bot
            bot_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='BOT',
                content=bot_response,
                sql_query_used=sql_query,
                metadata={
                    'data_count': len(response_data) if response_data else 0,
                    'error': sql_error
                }
            )
            
            return JsonResponse({
                'response': bot_response,
                'session_id': session_id,
                'message_id': bot_message.id,
                'data_count': len(response_data) if response_data else 0,
                'has_data': bool(response_data and len(response_data) > 0),
                'timestamp': bot_message.timestamp.isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)
        except Exception as e:
            print(f"💥 Erreur interne: {str(e)}")
            return JsonResponse({'error': f'Erreur interne: {str(e)}'}, status=500)

class ChatHistoryView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, session_id):
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
            messages = conversation.messages.all()
            
            history = []
            for msg in messages:
                history.append({
                    'type': msg.message_type,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'sql_query': msg.sql_query_used,
                    'data_count': msg.metadata.get('data_count', 0) if msg.metadata else 0
                })
            
            return JsonResponse({
                'session_id': session_id,
                'history': history,
                'conversation_created': conversation.created_at.isoformat()
            })
            
        except ChatConversation.DoesNotExist:
            return JsonResponse({'history': [], 'session_id': session_id})

class AccountingSummaryView(View):
    """Endpoint pour des résumés comptables prédéfinis"""
    
    def get(self, request):
        try:
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
                    SELECT numeroEcriture, date, libelle, reference 
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
            
            return JsonResponse({
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
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)