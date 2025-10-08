
from django.db import transaction
from rest_framework import serializers
from ..models import Account, JournalEntry, TransactionLine

def parse_compte(compte):
    try:
        numero, intitule = [s.strip() for s in compte.split(" - ", 1)]
    except Exception:
        raise ValueError("compte must be 'numero - intitule'")
    return numero, intitule

def create_journal_entry(validated_data):
    """
    Creates a JournalEntry and its TransactionLine children atomically.
    Expects validated_data to contain 'lines' as a list of dicts.
    """
    lines = validated_data.pop('lines', [])
    if not lines:
        raise serializers.ValidationError({"lines": "At least one transaction line is required."})

    # check balance
    total_debit = sum((l.get('debit') or 0) for l in lines)
    total_credit = sum((l.get('credit') or 0) for l in lines)
    if round(total_debit - total_credit, 2) != 0:
        raise serializers.ValidationError("Entry is not balanced: debit != credit")

    with transaction.atomic():
        entry = JournalEntry.objects.create(**validated_data)

        tl_objects = []
        for idx, line in enumerate(lines):
            compte = line.get('compte')
            try:
                account_num, account_name = parse_compte(compte)
            except ValueError as e:
                raise serializers.ValidationError({'lines': {idx: str(e)}})

            try:
                account = Account.objects.get(numero=account_num)
            except Account.DoesNotExist:
                raise serializers.ValidationError({'lines': {idx: f'Account {account_num} not found'}})

            # Prepare TransactionLine instance
            tl = TransactionLine(
                journal_entry=entry,
                account=account,
                accountNumber=account_num,
                accountName=account_name,
                debit=line.get('debit') or 0,
                credit=line.get('credit') or 0,
                calculatedAmount=line.get('calculatedAmount') or 0,
                percentage=line.get('percentage') or 0,
                nature=line.get('nature')
            )
            tl_objects.append(tl)

        TransactionLine.objects.bulk_create(tl_objects)

        return entry