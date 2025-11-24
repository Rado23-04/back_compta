
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from .utils import parse_data
from .utils_excel import read_excel_file
from .models import Account, JournalEntry
from .serializers import AccountSerializer, JournalEntrySerializer, AccountSoldeSerializer
from .serializers import ExcelImportSerializer
from .serializers import BulkImportSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

# Vue API pour lister et créer des comptes
@api_view(['GET', 'POST', 'PUT'])
def account_list(request, pk=None):
	"""
	GET : Liste tous les comptes
	POST : Crée un nouveau compte
	"""

	# Require authentication for all accounting endpoints to ensure per-user isolation
	if not request.user or not request.user.is_authenticated:
		return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

	if request.method == 'GET':
		accounts = Account.objects.filter(owner=request.user)
		serializer = AccountSerializer(accounts, many=True)
		return Response(serializer.data)
	
	elif request.method == 'POST':
		data = request.data
		many = isinstance(data, list)
		serializer = AccountSerializer(data=data, many=many)
		if serializer.is_valid():
			serializer.save(owner=request.user)
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'PUT':
		if not pk:
			return Response({"PK": "L'ID du compte est requis pour la mise à jour partielle."}, status=status.HTTP_400_BAD_REQUEST)
		try:
			account = Account.objects.get(pk=pk, owner=request.user)
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

	# Require authentication for all accounting endpoints to ensure per-user isolation
	if not request.user or not request.user.is_authenticated:
		return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
	if request.method == 'GET':
		entries = JournalEntry.objects.filter(owner=request.user).prefetch_related('lines')
		serializer = JournalEntrySerializer(entries, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)
	
	elif request.method == 'POST':
		# Permission: comptable and admin-comptable may create entries
		if getattr(request.user, 'role', None) not in ('comptable', 'admin-comptable'):
			return Response({'detail': 'You do not have permission to create journal entries.'}, status=status.HTTP_403_FORBIDDEN)

		data = parse_data(request.data)
		serializer = JournalEntrySerializer(data=data, context={'request': request})
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'PUT':
		if not pk:
			return Response({"PK": "L'ID de l'écriture est requis pour la mise à jour."}, status=status.HTTP_400_BAD_REQUEST)
		
		# Only admin-comptable may modify entries
		if getattr(request.user, 'role', None) != 'admin-comptable':
			return Response({'detail': 'You do not have permission to modify journal entries.'}, status=status.HTTP_403_FORBIDDEN)

		try:
			entry = JournalEntry.objects.get(pk=pk, owner=request.user)
		except JournalEntry.DoesNotExist:
			return Response({"Journal": "Écriture non trouvée."}, status=status.HTTP_404_NOT_FOUND)
		
		data = parse_data(request.data)
		
		serializer = JournalEntrySerializer(entry, data=data, context={'request': request})
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	
	elif request.method == 'DELETE':

		if not pk:
			return Response({"PK": "L'ID de l'écriture est requis pour la suppression."}, status=status.HTTP_400_BAD_REQUEST)
		
		# Only admin-comptable may delete entries
		if getattr(request.user, 'role', None) != 'admin-comptable':
			return Response({'detail': 'You do not have permission to delete journal entries.'}, status=status.HTTP_403_FORBIDDEN)

		try:
			entry = JournalEntry.objects.prefetch_related('lines').get(pk=pk, owner=request.user)
		except JournalEntry.DoesNotExist:
			return Response({"Journal": "Écriture non trouvée."}, status=status.HTTP_404_NOT_FOUND)
		
		entry.delete()

		return Response({"Journal":"Ecriture effacé"} ,status=status.HTTP_200_OK)



@api_view(['POST'])
def import_pcg(request, pk):
	"""Import a PCG JSON (sent as body) into the DB and assign created accounts
	to the owner of the Account with id=pk.

	- If the request body is a JSON array, it will be used as the PCG list.
	- If the body is empty, this action will return 400 (client must send PCG).
	"""

	# Authentication: require logged user
	if not request.user or not request.user.is_authenticated:
		return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

	# Find target account and owner
	target = get_object_or_404(Account, pk=pk)
	owner = target.owner
	# If the target has no owner, assign the importing user as owner.
	# If the target has an owner different from the requester, only allow admins to import.
	if owner is None:
		owner = request.user
		# persist the owner on the target account to keep ownership consistent
		target.owner = owner
		target.save()
	elif owner != request.user and getattr(request.user, 'role', None) != 'admin-comptable':
		return Response({'detail': 'You do not have permission to import into this account.'}, status=status.HTTP_403_FORBIDDEN)

	data = request.data
	if not data:
		return Response({'detail': 'Please provide PCG JSON array in request body.'}, status=status.HTTP_400_BAD_REQUEST)

	# Accept wrapper objects like {"items": [...]} or raw list
	if isinstance(data, dict):
		data = data.get('items') or data.get('pcg') or [data]

	if not isinstance(data, list):
		return Response({'detail': 'Expected a JSON array.'}, status=status.HTTP_400_BAD_REQUEST)

	existing = set(Account.objects.filter(owner=owner).values_list('numero', flat=True))
	to_create = []
	for item in data:
		numero = item.get('numero')
		if not numero:
			continue
		if numero in existing:
			continue
		acct = Account(
			owner=owner,
			numero=numero,
			intitule=item.get('intitule', ''),
			classe=item.get('classe') or 0,
			type=item.get('type', ''),
			nature=item.get('nature'),
			soldeInitial=item.get('soldeInitial') or 0,
		)
		to_create.append(acct)

	created_count = 0
	if to_create:
		with transaction.atomic():
			created = Account.objects.bulk_create(to_create)
			created_count = len(created)

	return Response({'created': created_count}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@api_view(['POST'])
def import_entries_excel(request):
	"""Endpoint: POST /entries/import-excel/
	Accepts multipart/form-data with field 'file' (xlsx)."""
	# Permission: same as entry_list POST (comptable or admin-comptable)
	if not request.user or not request.user.is_authenticated:
		return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
	if getattr(request.user, 'role', None) not in ('comptable', 'admin-comptable'):
		return Response({'detail': 'You do not have permission to import entries.'}, status=status.HTTP_403_FORBIDDEN)

	# file must be present
	upload = request.FILES.get('file')
	if not upload:
		return Response({'detail': 'Missing file field (multipart/form-data expected with field name "file").'}, status=status.HTTP_400_BAD_REQUEST)

	# parse
	try:
		rows = read_excel_file(upload)
	except Exception as e:
		return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	# validate via serializers
	serializer = ExcelImportSerializer(data={'lines': rows}, context={'request': request})
	if not serializer.is_valid():
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	result = serializer.save()
	return Response({'created_entries': result.get('created_entries')}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def import_entries_bulk(request):
	"""Endpoint: POST /entries/bulk-import/
	Accepts JSON body with { entries: [ ... ] } and creates JournalEntry + TransactionLine.
	"""
	# Auth + role check
	if not request.user or not request.user.is_authenticated:
		return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
	if getattr(request.user, 'role', None) not in ('comptable', 'admin-comptable'):
		return Response({'detail': 'You do not have permission to import entries.'}, status=status.HTTP_403_FORBIDDEN)

	serializer = BulkImportSerializer(data=request.data, context={'request': request})
	if not serializer.is_valid():
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	try:
		result = serializer.save()
	except Exception as e:
		# if duplicate detected, return 409
		msg = str(e)
		if 'Duplicate entry' in msg:
			return Response({'detail': msg}, status=status.HTTP_409_CONFLICT)
		return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

	# serialize created entries for response
	entries = result.get('entries', [])
	out = JournalEntrySerializer(entries, many=True)
	return Response({'created': result.get('created_count', 0), 'entries': out.data}, status=status.HTTP_201_CREATED)