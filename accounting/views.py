
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .utils import parse_data
from .models import Account, JournalEntry
from .serializers import AccountSerializer, JournalEntrySerializer, AccountSoldeSerializer

# Vue API pour lister et créer des comptes
@api_view(['GET', 'POST', 'PUT'])
def account_list(request, pk=None):
	"""
	GET : Liste tous les comptes
	POST : Crée un nouveau compte
	"""
	if request.method == 'GET':
		accounts = Account.objects.all()
		serializer = AccountSerializer(accounts, many=True)
		return Response(serializer.data)
	
	elif request.method == 'POST':
		data = request.data
		many = isinstance(data, list)
		serializer = AccountSerializer(data=data, many=many)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'PUT':
		if not pk:
			return Response({"PK": "L'ID du compte est requis pour la mise à jour partielle."}, status=status.HTTP_400_BAD_REQUEST)
		try:
			account = Account.objects.get(pk=pk)
		except Account.DoesNotExist:
			return Response({"Account": "Compte non trouvé."}, status=status.HTTP_404_NOT_FOUND)

		serializer = AccountSoldeSerializer(account, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			full = AccountSerializer(account)
			return Response(full.data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vue API pour lister et créer des écritures comptables
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def entry_list(request, pk=None):
	"""
	GET : Liste toutes les écritures
	POST : Crée une nouvelle écriture avec ses lignes
	"""
	if request.method == 'GET':
		entries = JournalEntry.objects.prefetch_related('lines').all()
		serializer = JournalEntrySerializer(entries, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)
	
	elif request.method == 'POST':
		data = parse_data(request.data)
		serializer = JournalEntrySerializer(data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'PUT':
		if not pk:
			return Response({"PK": "L'ID de l'écriture est requis pour la mise à jour."}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			entry = JournalEntry.objects.get(pk=pk)
		except JournalEntry.DoesNotExist:
			return Response({"Journal": "Écriture non trouvée."}, status=status.HTTP_404_NOT_FOUND)
		
		data = parse_data(request.data)
		
		serializer = JournalEntrySerializer(entry, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'DELETE':

		if not pk:
			return Response({"PK": "L'ID de l'écriture est requis pour la suppression."}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			entry = JournalEntry.objects.prefetch_related('lines').get(pk=pk)
		except JournalEntry.DoesNotExist:
			return Response({"Journal": "Écriture non trouvée."}, status=status.HTTP_404_NOT_FOUND)
		
		entry.delete()

		return Response({"Journal":"Ecriture effacé"} ,status=status.HTTP_200_OK)