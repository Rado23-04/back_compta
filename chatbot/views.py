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

class FinancialAnalyzer:
    """Classe dédiée à l'analyse financière avancée"""
    
    def __init__(self, chat_bot):
        self.chat_bot = chat_bot
    
    def generate_advanced_analysis(self, user_question, sql_data, sql_query):
        """Génère des analyses avancées avec interprétation financière"""
        
        # Détection du type d'analyse demandée
        analysis_type = self.detect_analysis_type(user_question)
        print(f"🔍 Type d'analyse détecté: {analysis_type}")
        
        analysis_handlers = {
            'FINANCIAL_HEALTH': self._analyze_financial_health,
            'CASH_FLOW': self._analyze_cash_flow,
            'PROFITABILITY': self._analyze_profitability,
            'BALANCE_SHEET_DETAILED': self._analyze_balance_sheet_detailed,
            'INCOME_STATEMENT_DETAILED': self._analyze_income_statement_detailed,
            'ACCOUNT_ANALYSIS': self._analyze_account_trends,
            'COMPARATIVE_ANALYSIS': self._analyze_comparative_data,
            'FORECAST': self._generate_forecast
        }
        
        handler = analysis_handlers.get(analysis_type, self._generate_smart_insights)
        return handler(user_question, sql_data, sql_query)

    def detect_analysis_type(self, user_question):
        """Détecte le type d'analyse demandé"""
        question_lower = user_question.lower()
        
        analysis_patterns = {
            'FINANCIAL_HEALTH': [
                r'santé.*financière', r'situation.*financière', r'équilibre.*financier',
                r'solidité', r'rentabilité', r'performance.*financière'
            ],
            'CASH_FLOW': [
                r'trésorerie', r'cash.?flow', r'flux.*trésorerie', r'liquidité',
                r'besoin.*fond.*roulement', r'bfr'
            ],
            'PROFITABILITY': [
                r'profitabilité', r'marge', r'rentabilité', r'bénéfice',
                r'ratio.*profit', r'taux.*marge'
            ],
            'BALANCE_SHEET_DETAILED': [
                r'bilan.*détaillé', r'analyse.*bilan', r'structure.*financière',
                r'actif.*passif', r'patrimoine'
            ],
            'INCOME_STATEMENT_DETAILED': [
                r'compte.*résultat.*détaillé', r'analyse.*résultat',
                r'charges.*produits', r'évolution.*résultat'
            ],
            'ACCOUNT_ANALYSIS': [
                r'analyse.*compte', r'évolution.*compte', r'tendance.*compte',
                r'solde.*compte.*(\d{1,6})', r'historique.*compte'
            ],
            'COMPARATIVE_ANALYSIS': [
                r'comparaison', r'comparer', r'évolution', r'tendance',
                r'variation', r'progress'
            ],
            'FORECAST': [
                r'prévision', r'projection', r'estimation', r'prédire',
                r'avenir', r'futur'
            ]
        }
        
        scores = {}
        for analysis_type, patterns in analysis_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    score += 2
            scores[analysis_type] = score
        
        best_analysis = max(scores.items(), key=lambda x: x[1])
        return best_analysis[0] if best_analysis[1] > 0 else 'GENERIC_INSIGHTS'

    def _analyze_financial_health(self, user_question, data, sql_query):
        """Analyse approfondie de la santé financière"""
        if not data:
            return "❌ Données insuffisantes pour analyser la santé financière."
        
        # Récupérer les données financières de base
        financial_data = self._extract_financial_metrics(data)
        
        analysis = "🏥 **ANALYSE DE SANTÉ FINANCIÈRE**\n\n"
        
        # Score de santé financière
        health_score = self._calculate_financial_health_score(financial_data)
        analysis += f"**Score de santé financière**: {health_score}/10\n\n"
        
        # Points forts
        analysis += "✅ **POINTS FORTS**:\n"
        if financial_data.get('current_ratio', 0) > 1.5:
            analysis += "• Excellente liquidité à court terme\n"
        if financial_data.get('profit_margin', 0) > 0.1:
            analysis += "• Bonne rentabilité des activités\n"
        if financial_data.get('debt_ratio', 0) < 0.6:
            analysis += "• Faible endettement\n"
        if financial_data.get('asset_growth', 0) > 0.05:
            analysis += "• Croissance patrimoniale positive\n"
        
        # Points d'attention
        analysis += "\n⚠️ **POINTS D'ATTENTION**:\n"
        if financial_data.get('current_ratio', 0) < 1:
            analysis += "• Liquidité insuffisante à court terme\n"
        if financial_data.get('profit_margin', 0) < 0:
            analysis += "• Rentabilité négative\n"
        if financial_data.get('debt_ratio', 0) > 0.8:
            analysis += "• Niveau d'endettement élevé\n"
        
        # Recommandations
        analysis += "\n💡 **RECOMMANDATIONS**:\n"
        if financial_data.get('current_ratio', 0) < 1:
            analysis += "• Améliorer la trésorerie et réduire les dettes court terme\n"
        if financial_data.get('profit_margin', 0) < 0:
            analysis += "• Revoir la structure des coûts et augmenter la marge\n"
        if financial_data.get('asset_turnover', 0) < 0.5:
            analysis += "• Optimiser l'utilisation des actifs\n"
        
        return analysis

    def _analyze_cash_flow(self, user_question, data, sql_query):
        """Analyse de la trésorerie et des flux financiers"""
        if not data:
            return "❌ Données insuffisantes pour analyser la trésorerie."
        
        cash_data = self._extract_cash_metrics(data)
        
        analysis = "💧 **ANALYSE DE TRÉSORERIE**\n\n"
        
        # État de la trésorerie
        cash_position = cash_data.get('cash_balance', 0)
        analysis += f"**Position de trésorerie**: {cash_position:,.2f} €\n\n"
        
        # Analyse des flux
        analysis += "📊 **ANALYSE DES FLUX**:\n"
        
        operating_cash = cash_data.get('operating_cash_flow', 0)
        if operating_cash > 0:
            analysis += f"• Flux opérationnel positif: {operating_cash:,.2f} € ✅\n"
        else:
            analysis += f"• Flux opérationnel négatif: {operating_cash:,.2f} € ⚠️\n"
        
        investing_cash = cash_data.get('investing_cash_flow', 0)
        if investing_cash < 0:
            analysis += f"• Investissements: {abs(investing_cash):,.2f} € 📈\n"
        
        financing_cash = cash_data.get('financing_cash_flow', 0)
        if financing_cash != 0:
            analysis += f"• Financement: {financing_cash:,.2f} €\n"
        
        # Recommandations trésorerie
        analysis += "\n🎯 **CONSEILS TRÉSORERIE**:\n"
        if cash_position < 10000:
            analysis += "• Renforcer la trésorerie disponible\n"
        if operating_cash < 0:
            analysis += "• Améliorer la génération de cash opérationnel\n"
        
        return analysis

    def _analyze_profitability(self, user_question, data, sql_query):
        """Analyse détaillée de la rentabilité"""
        if not data:
            return "❌ Données insuffisantes pour analyser la rentabilité."
        
        profit_data = self._extract_profitability_metrics(data)
        
        analysis = "📈 **ANALYSE DE RENTABILITÉ**\n\n"
        
        # Marges
        gross_margin = profit_data.get('gross_margin', 0)
        net_margin = profit_data.get('net_margin', 0)
        
        analysis += f"**Marge brute**: {gross_margin:.1%}\n"
        analysis += f"**Marge nette**: {net_margin:.1%}\n\n"
        
        # Interprétation des marges
        analysis += "📋 **INTERPRÉTATION**:\n"
        if net_margin > 0.15:
            analysis += "• Excellente rentabilité 🎯\n"
        elif net_margin > 0.05:
            analysis += "• Bonne rentabilité ✅\n"
        elif net_margin > 0:
            analysis += "• Rentabilité modérée ⚠️\n"
        else:
            analysis += "• Rentabilité négative ❌\n"
        
        # Analyse des coûts
        analysis += "\n💰 **ANALYSE DES COÛTS**:\n"
        cost_ratio = profit_data.get('cost_ratio', 0)
        analysis += f"• Ratio charges/produits: {cost_ratio:.1%}\n"
        
        if cost_ratio > 0.9:
            analysis += "• Structure de coûts à optimiser\n"
        
        return analysis

    def _analyze_balance_sheet_detailed(self, user_question, data, sql_query):
        """Analyse détaillée du bilan"""
        if not data:
            return "❌ Données insuffisantes pour analyser le bilan."
        
        balance_data = self._extract_balance_sheet_metrics(data)
        
        analysis = "⚖️ **ANALYSE DÉTAILLÉE DU BILAN**\n\n"
        
        # Structure du bilan
        analysis += "🏗️ **STRUCTURE DU BILAN**:\n"
        analysis += f"• Actif total: {balance_data.get('total_assets', 0):,.2f} €\n"
        analysis += f"• Passif total: {balance_data.get('total_liabilities', 0):,.2f} €\n"
        analysis += f"• Capitaux propres: {balance_data.get('equity', 0):,.2f} €\n\n"
        
        # Ratios financiers
        analysis += "📊 **RATIOS FINANCIERS**:\n"
        
        debt_ratio = balance_data.get('debt_ratio', 0)
        analysis += f"• Ratio d'endettement: {debt_ratio:.1%}\n"
        
        current_ratio = balance_data.get('current_ratio', 0)
        analysis += f"• Ratio de liquidité: {current_ratio:.2f}\n"
        
        # Interprétation
        analysis += "\n🔍 **INTERPRÉTATION**:\n"
        if debt_ratio < 0.5:
            analysis += "• Structure financière saine ✅\n"
        elif debt_ratio < 0.7:
            analysis += "• Endettement modéré ⚠️\n"
        else:
            analysis += "• Endettement élevé ❌\n"
        
        if current_ratio > 1.5:
            analysis += "• Excellente liquidité ✅\n"
        elif current_ratio > 1:
            analysis += "• Liquidité acceptable ⚠️\n"
        else:
            analysis += "• Problème de liquidité ❌\n"
        
        return analysis

    def _analyze_income_statement_detailed(self, user_question, data, sql_query):
        """Analyse détaillée du compte de résultat"""
        if not data:
            return "❌ Données insuffisantes pour analyser le compte de résultat."
        
        income_data = self._extract_income_statement_metrics(data)
        
        analysis = "📊 **ANALYSE DÉTAILLÉE DU COMPTE DE RÉSULTAT**\n\n"
        
        # Chiffre d'affaires et résultat
        analysis += "💰 **CHIFFRE D'AFFAIRES ET RÉSULTAT**:\n"
        analysis += f"• Produits totaux: {income_data.get('total_revenue', 0):,.2f} €\n"
        analysis += f"• Charges totales: {income_data.get('total_expenses', 0):,.2f} €\n"
        analysis += f"• Résultat net: {income_data.get('net_income', 0):,.2f} €\n\n"
        
        # Structure des charges
        analysis += "📋 **STRUCTURE DES CHARGES**:\n"
        expense_breakdown = income_data.get('expense_breakdown', {})
        for expense_type, amount in expense_breakdown.items():
            if amount > 0:
                percentage = (amount / income_data.get('total_revenue', 1)) * 100
                analysis += f"• {expense_type}: {percentage:.1f}% du CA\n"
        
        # Analyse de performance
        analysis += "\n🎯 **PERFORMANCE**:\n"
        growth_rate = income_data.get('revenue_growth', 0)
        if growth_rate > 0.1:
            analysis += f"• Croissance forte: +{growth_rate:.1%} 📈\n"
        elif growth_rate > 0:
            analysis += f"• Croissance modérée: +{growth_rate:.1%} ✅\n"
        else:
            analysis += f"• Décroissance: {growth_rate:.1%} ⚠️\n"
        
        return analysis

    def _analyze_account_trends(self, user_question, data, sql_query):
        """Analyse des tendances par compte"""
        if not data:
            return "❌ Données insuffisantes pour analyser les tendances."
        
        analysis = "📈 **ANALYSE DES TENDANCES PAR COMPTE**\n\n"
        
        # Regrouper par compte si possible
        account_data = {}
        for item in data:
            account_num = item.get('numero', 'Inconnu')
            if account_num not in account_data:
                account_data[account_num] = []
            account_data[account_num].append(item)
        
        for account_num, items in list(account_data.items())[:5]:  # Limiter à 5 comptes
            if len(items) > 1:
                analysis += f"**Compte {account_num}**:\n"
                # Calculer l'évolution
                first_solde = self.chat_bot._extract_numeric_value(items[0], 'solde')
                last_solde = self.chat_bot._extract_numeric_value(items[-1], 'solde')
                
                if first_solde != 0:
                    evolution = ((last_solde - first_solde) / abs(first_solde)) * 100
                    analysis += f"• Évolution: {evolution:+.1f}%\n"
                analysis += "\n"
        
        return analysis

    def _analyze_comparative_data(self, user_question, data, sql_query):
        """Analyse comparative des données"""
        if not data or len(data) < 2:
            return "❌ Données insuffisantes pour une analyse comparative."
        
        analysis = "📊 **ANALYSE COMPARATIVE**\n\n"
        
        # Statistiques descriptives
        numeric_values = []
        for item in data:
            for key, value in item.items():
                if isinstance(value, (int, float)) and value != 0:
                    numeric_values.append(value)
        
        if numeric_values:
            analysis += f"• Valeur moyenne: {sum(numeric_values)/len(numeric_values):,.2f} €\n"
            analysis += f"• Écart-type: {self._calculate_std_dev(numeric_values):,.2f} €\n"
            analysis += f"• Coefficient de variation: {self._calculate_std_dev(numeric_values)/(sum(numeric_values)/len(numeric_values)) if sum(numeric_values) != 0 else 0:.1%}\n\n"
        
        # Distribution
        analysis += "📋 **DISTRIBUTION**:\n"
        analysis += f"• Minimum: {min(numeric_values):,.2f} €\n"
        analysis += f"• Maximum: {max(numeric_values):,.2f} €\n"
        analysis += f"• Médiane: {sorted(numeric_values)[len(numeric_values)//2]:,.2f} €\n"
        
        return analysis

    def _generate_forecast(self, user_question, data, sql_query):
        """Génère des prévisions basées sur les données historiques"""
        if not data or len(data) < 3:
            return "❌ Données historiques insuffisantes pour une prévision."
        
        analysis = "🔮 **PRÉVISIONS ET TENDANCES**\n\n"
        
        # Simple prévision linéaire
        trend = self._calculate_trend(data)
        if trend:
            analysis += f"• Tendance détectée: {'📈 Hausse' if trend > 0 else '📉 Baisse'}\n"
            analysis += f"• Pente moyenne: {trend:+.2f} par période\n\n"
        
        analysis += "💡 **RECOMMANDATIONS STRATÉGIQUES**:\n"
        if trend and trend > 0:
            analysis += "• Poursuivre la stratégie actuelle\n"
            analysis += "• Investir dans la croissance\n"
        elif trend and trend < 0:
            analysis += "• Revoir la stratégie commerciale\n"
            analysis += "• Optimiser les coûts\n"
        else:
            analysis += "• Stabiliser les performances\n"
            analysis += "• Diversifier les activités\n"
        
        return analysis

    def _generate_smart_insights(self, user_question, data, sql_query):
        """Génère des insights intelligents basés sur les données"""
        if not data:
            return "🤔 Je n'ai pas trouvé de données pour générer des insights."
        
        analysis = "💡 **INSIGHTS INTELLIGENTS**\n\n"
        
        # Détection de patterns
        patterns = self._detect_data_patterns(data)
        
        for pattern, insight in patterns.items():
            analysis += f"• {insight}\n"
        
        # Recommandations basées sur les données
        recommendations = self._generate_data_recommendations(data)
        if recommendations:
            analysis += "\n🎯 **RECOMMANDATIONS**:\n"
            for rec in recommendations[:3]:  # Limiter à 3 recommandations
                analysis += f"• {rec}\n"
        
        return analysis

    # ==================== MÉTHODES DE SUPPORT POUR L'ANALYSE ====================

    def _extract_financial_metrics(self, data):
        """Extrait les métriques financières des données"""
        metrics = {
            'total_assets': 0,
            'total_liabilities': 0,
            'current_ratio': 0,
            'debt_ratio': 0,
            'profit_margin': 0,
            'asset_growth': 0,
            'asset_turnover': 0
        }
        
        # Implémentation simplifiée - à adapter selon votre structure de données
        for item in data:
            if 'solde' in item:
                solde = self.chat_bot._extract_numeric_value(item, 'solde')
                if solde > 0:
                    metrics['total_assets'] += solde
                else:
                    metrics['total_liabilities'] += abs(solde)
        
        # Calcul des ratios
        if metrics['total_liabilities'] > 0:
            metrics['current_ratio'] = metrics['total_assets'] / metrics['total_liabilities'] if metrics['total_liabilities'] > 0 else 0
            metrics['debt_ratio'] = metrics['total_liabilities'] / (metrics['total_assets'] + metrics['total_liabilities'])
        
        return metrics

    def _extract_cash_metrics(self, data):
        """Extrait les métriques de trésorerie"""
        metrics = {
            'cash_balance': 0,
            'operating_cash_flow': 0,
            'investing_cash_flow': 0,
            'financing_cash_flow': 0
        }
        
        # Implémentation simplifiée
        for item in data:
            if 'numero' in item and str(item['numero']).startswith('5'):  # Comptes de trésorerie
                metrics['cash_balance'] += self.chat_bot._extract_numeric_value(item, 'solde')
        
        return metrics

    def _extract_profitability_metrics(self, data):
        """Extrait les métriques de rentabilité"""
        metrics = {
            'gross_margin': 0,
            'net_margin': 0,
            'cost_ratio': 0
        }
        
        total_revenue = 0
        total_costs = 0
        
        for item in data:
            if 'numero' in item:
                account_num = str(item['numero'])
                solde = self.chat_bot._extract_numeric_value(item, 'solde')
                
                if account_num.startswith('7'):  # Produits
                    total_revenue += solde
                elif account_num.startswith('6'):  # Charges
                    total_costs += solde
        
        if total_revenue > 0:
            metrics['gross_margin'] = (total_revenue - total_costs) / total_revenue
            metrics['net_margin'] = (total_revenue - total_costs) / total_revenue
            metrics['cost_ratio'] = total_costs / total_revenue
        
        return metrics

    def _extract_balance_sheet_metrics(self, data):
        """Extrait les métriques du bilan"""
        return self._extract_financial_metrics(data)  # Réutilise la même logique pour l'instant

    def _extract_income_statement_metrics(self, data):
        """Extrait les métriques du compte de résultat"""
        metrics = {
            'total_revenue': 0,
            'total_expenses': 0,
            'net_income': 0,
            'revenue_growth': 0,
            'expense_breakdown': {}
        }
        
        for item in data:
            if 'numero' in item:
                account_num = str(item['numero'])
                solde = self.chat_bot._extract_numeric_value(item, 'solde')
                
                if account_num.startswith('7'):  # Produits
                    metrics['total_revenue'] += solde
                    account_class = account_num[:2]
                    metrics['expense_breakdown'][f'Produits classe {account_class}'] = \
                        metrics['expense_breakdown'].get(f'Produits classe {account_class}', 0) + solde
                elif account_num.startswith('6'):  # Charges
                    metrics['total_expenses'] += solde
                    account_class = account_num[:2]
                    metrics['expense_breakdown'][f'Charges classe {account_class}'] = \
                        metrics['expense_breakdown'].get(f'Charges classe {account_class}', 0) + solde
        
        metrics['net_income'] = metrics['total_revenue'] - metrics['total_expenses']
        
        return metrics

    def _calculate_financial_health_score(self, financial_data):
        """Calcule un score de santé financière (0-10)"""
        score = 5  # Score de base
        
        # Facteurs positifs
        if financial_data.get('current_ratio', 0) > 1.5:
            score += 2
        if financial_data.get('profit_margin', 0) > 0.1:
            score += 2
        if financial_data.get('debt_ratio', 0) < 0.5:
            score += 1
        
        # Facteurs négatifs
        if financial_data.get('current_ratio', 0) < 1:
            score -= 2
        if financial_data.get('profit_margin', 0) < 0:
            score -= 2
        if financial_data.get('debt_ratio', 0) > 0.8:
            score -= 1
        
        return max(0, min(10, score))

    def _calculate_std_dev(self, values):
        """Calcule l'écart-type"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _calculate_trend(self, data):
        """Calcule la tendance des données"""
        if len(data) < 2:
            return None
        
        numeric_values = []
        for item in data:
            for key, value in item.items():
                if isinstance(value, (int, float)) and value != 0:
                    numeric_values.append(value)
                    break  # Prendre une seule valeur par ligne
        
        if len(numeric_values) < 2:
            return None
        
        # Régression linéaire simple
        x = list(range(len(numeric_values)))
        y = numeric_values
        
        n = len(x)
        if n == 0:
            return None
            
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return None

    def _detect_data_patterns(self, data):
        """Détecte des patterns dans les données"""
        patterns = {}
        
        if not data:
            return patterns
        
        # Pattern de croissance/décroissance
        trend = self._calculate_trend(data)
        if trend and trend > 0.1:
            patterns['growth'] = "Tendance à la hausse détectée"
        elif trend and trend < -0.1:
            patterns['decline'] = "Tendance à la baisse détectée"
        
        # Pattern de concentration
        if len(data) > 5:
            values = [self.chat_bot._extract_numeric_value(item, 'solde') for item in data if 'solde' in item]
            if values:
                max_value = max(values)
                if max_value > sum(values) * 0.5:  # Une valeur représente plus de 50%
                    patterns['concentration'] = "Fort concentration sur quelques éléments"
        
        return patterns

    def _generate_data_recommendations(self, data):
        """Génère des recommandations basées sur les données"""
        recommendations = []
        
        if not data:
            return recommendations
        
        # Analyser la structure des données pour faire des recommandations
        total_debit = sum(self.chat_bot._extract_numeric_value(item, 'debit') for item in data if 'debit' in item)
        total_credit = sum(self.chat_bot._extract_numeric_value(item, 'credit') for item in data if 'credit' in item)
        
        if total_debit > total_credit * 1.5:
            recommendations.append("Équilibrez les débits et crédits pour une meilleure gestion")
        
        # Recommandations basées sur les comptes
        account_types = {}
        for item in data:
            if 'numero' in item:
                account_class = str(item['numero'])[0]  # Première classe
                account_types[account_class] = account_types.get(account_class, 0) + 1
        
        if '6' in account_types and account_types['6'] > 10:
            recommendations.append("Revoyez la structure des charges (trop de comptes de classe 6)")
        
        if '4' in account_types and account_types['4'] > 5:
            recommendations.append("Surveillez les comptes fournisseurs (classe 4)")
        
        return recommendations

class AccountingChatBotView(View):
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.gemini_available = False
        self.financial_analyzer = FinancialAnalyzer(self)
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
        
        # Vérifier si une analyse avancée est demandée
        if any(keyword in user_question.lower() for keyword in ['analyse', 'interprétation', 'bilan', 'tendance', 'évolution', 'ratio', 'santé']):
            print("🔍 Analyse avancée demandée")
            return self.financial_analyzer.generate_advanced_analysis(user_question, sql_data, sql_query)
        
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
            print(f"🎯 Session ID: {session_id}")
            
            # Réinitialisation si nécessaire
            if not self.gemini_available:
                self._initialize_gemini()
            
            # ✅ AMÉLIORATION: Gestion robuste de la conversation
            try:
                user, created = User.objects.get_or_create(username='chatbot_user')
                conversation, created = ChatConversation.objects.get_or_create(
                    session_id=session_id, 
                    defaults={
                        'user': user,
                        'title': user_question[:50] + '...' if len(user_question) > 50 else user_question
                    }
                )
                
                # ✅ Mise à jour du titre si la conversation existe déjà
                if not created:
                    # Garder le titre original ou mettre à jour si c'est le premier message
                    if not conversation.title or conversation.title == 'Nouvelle conversation':
                        conversation.title = user_question[:50] + '...' if len(user_question) > 50 else user_question
                        conversation.save()
                
            except Exception as e:
                print(f"❌ Erreur gestion conversation: {str(e)}")
                return JsonResponse({'error': 'Erreur gestion conversation'}, status=500)
            
            # ✅ Enregistrement du message utilisateur
            try:
                user_message = ChatMessage.objects.create(
                    conversation=conversation,
                    message_type='USER',
                    content=user_question
                )
                print(f"✅ Message utilisateur enregistré: {user_message.id}")
            except Exception as e:
                print(f"❌ Erreur enregistrement message utilisateur: {str(e)}")
            
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
            
            # Génération de la réponse
            if sql_error:
                bot_response = "❌ Difficulté technique avec cette requête. Reformulez votre question."
            else:
                if self.gemini_available:
                    conversational_response = self.generate_conversational_response(user_question, response_data, sql_query)
                    if conversational_response and len(conversational_response) > 30:
                        bot_response = conversational_response
                    else:
                        bot_response = self.generate_precise_response(user_question, response_data, sql_query)
                else:
                    bot_response = self.generate_precise_response(user_question, response_data, sql_query)
            
            print(f"📤 Réponse générée: {len(bot_response)} caractères")
            
            # ✅ ENREGISTREMENT ROBUSTE DE LA RÉPONSE DU BOT
            try:
                bot_message = ChatMessage.objects.create(
                    conversation=conversation,
                    message_type='BOT',
                    content=bot_response,
                    sql_query_used=sql_query,
                    metadata={
                        'data_count': len(response_data) if response_data else 0,
                        'gemini_used': gemini_used,
                        'gemini_available': self.gemini_available,
                        'error': sql_error,
                        'user_question': user_question  # ✅ Stocker aussi la question originale
                    }
                )
                print(f"✅ Message bot enregistré: {bot_message.id}")
                
                # ✅ Mise à jour du timestamp de la conversation
                conversation.save()  # Cela met à jour le champ updated_at automatiquement
                
            except Exception as e:
                print(f"❌ Erreur enregistrement message bot: {str(e)}")
                # Continuer même si l'enregistrement échoue
            
            return JsonResponse({
                'response': bot_response,
                'session_id': session_id,  # ✅ Retourner le même session_id
                'data_count': len(response_data) if response_data else 0,
                'has_data': bool(response_data and len(response_data) > 0),
                'gemini_used': gemini_used,
                'gemini_available': self.gemini_available,
                'conversation_id': conversation.id,  # ✅ Retourner l'ID de conversation
                'timestamp': bot_message.timestamp.isoformat() if 'bot_message' in locals() else datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"💥 Erreur globale: {str(e)}")
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
        
        return JsonResponse({
            'gemini_available': chatbot.gemini_available,
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

class CreateConversationView(View):
    """Vue pour créer une nouvelle conversation"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id', f"session_{datetime.now().timestamp()}")
            title = data.get('title', 'Nouvelle conversation')
            
            user, created = User.objects.get_or_create(username='chatbot_user')
            conversation, created = ChatConversation.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'user': user,
                    'title': title
                }
            )
            
            return JsonResponse({
                'success': True,
                'session_id': conversation.session_id,
                'conversation_id': conversation.id,
                'title': conversation.title,
                'created': created
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)