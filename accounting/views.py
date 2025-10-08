
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Account, JournalEntry
from .serializers import AccountSerializer, JournalEntrySerializer

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
		accounts = request.data
		for account in accounts:
			serializer = AccountSerializer(account)
			if serializer.is_valid():
				serializer.save()
				return Response(serializer.data, status=status.HTTP_201_CREATED)
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vue API pour lister et créer des écritures comptables
@api_view(['GET', 'POST'])
def entry_list(request):
	"""
	GET : Liste toutes les écritures
	POST : Crée une nouvelle écriture avec ses lignes
	"""
	if request.method == 'GET':
		entries = JournalEntry.objects.all()
		serializer = JournalEntrySerializer(entries, many=True)
		return Response(serializer.data)
	elif request.method == 'POST':
		serializer = JournalEntrySerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
