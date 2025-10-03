
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import Account, JournalEntry
from .serializers import AccountSerializer, JournalEntrySerializer
from .services import JournalService
from datetime import datetime

# Vue API pour lister et créer des comptes
@api_view(['GET', 'POST'])
def account_list(request):
	"""
	GET : Liste tous les comptes
	POST : Crée un nouveau compte
	"""
	if request.method == 'GET':
		accounts = Account.objects.all()
		serializer = AccountSerializer(accounts, many=True)
		return Response(serializer.data)
	elif request.method == 'POST':
		serializer = AccountSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vue API pour lister et créer des écritures comptables
@api_view(['GET', 'POST'])
def entry_list(request):
    """
    GET : Liste toutes les écritures avec filtres optionnels
    POST : Crée une nouvelle écriture avec ses lignes
    """
    if request.method == 'GET':
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        account_id = request.query_params.get('account_id')

        query = JournalEntry.objects.all()
        if start_date:
            query = query.filter(date__gte=start_date)
        if end_date:
            query = query.filter(date__lte=end_date)
        if account_id:
            query = query.filter(lines__account_id=account_id)

        entries = query.distinct().order_by('date')
        serializer = JournalEntrySerializer(entries, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        try:
            entry = JournalService.create_journal_entry(request.data)
            serializer = JournalEntrySerializer(entry)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def balance_sheet(request):
    """
    GET : Retourne le bilan comptable pour une période donnée
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    try:
        balance_data = JournalService.get_balance_sheet(start_date, end_date)
        return Response(balance_data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def account_statement(request, account_id):
    """
    GET : Retourne le relevé d'un compte pour une période donnée
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    try:
        statement = JournalService.get_account_statement(account_id, start_date, end_date)
        return Response(statement)
    except Account.DoesNotExist:
        return Response({'error': 'Compte non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
