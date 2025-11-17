
from django.db import transaction
from rest_framework import serializers
from ..models import Account, JournalEntry, TransactionLine
from ..utils import check_balance#, update_account_solde

def create_journal_entry(validated_data, user=None):

    lines = validated_data.pop('lines', [])

    if not lines:
        raise serializers.ValidationError({"Transactions": "Au moins une transaction est requis."})

    if check_balance(lines) is not True:
        raise serializers.ValidationError("Les transactions ne sont pas en équilibre: debit != credit")

    with transaction.atomic():

        # Ensure the created JournalEntry is owned by the authenticated user (if provided)
        if user is not None:
            validated_data['owner'] = user

        journal_entry = JournalEntry.objects.create(**validated_data)
        
        tListObject = []

        for idx, line in enumerate(lines):

            # Ensure the account belongs to the user (if user provided), otherwise raise
            if user is not None:
                try:
                    account = Account.objects.get(numero=line["accountNumber"], owner=user)
                except Account.DoesNotExist:
                    raise serializers.ValidationError({"account": f"Account {line.get('accountNumber')} not found for this user."})
            else:
                account = Account.objects.get(numero=line["accountNumber"])

            tLine = TransactionLine(
                journal_entry=journal_entry,
                account=account,
                accountNumber=account.numero,
                accountName=account.intitule,
                debit=line.get('debit') or 0,
                credit=line.get('credit') or 0,
                calculatedAmount=line.get('calculatedAmount') or 0,
                percentage=line.get('percentage') or 0,
                nature=line.get('nature')
            )

            tListObject.append(tLine)

            #update_account_solde(account.id, tLine.debit, tLine.credit)

        TransactionLine.objects.bulk_create(tListObject)

    return journal_entry

def update_journal_entry(instance, validated_data, user=None):

    lines = validated_data.pop('lines')

    if not lines:
        raise serializers.ValidationError({"Transactions": "Au moins une transaction est requis."})

    if check_balance(lines) is not True:
        raise serializers.ValidationError("Les transactions ne sont pas en équilibre: debit != credit")


    with transaction.atomic():

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        instance.lines.all().delete()

        tListObject = []
        
        for idx, line in enumerate(lines):

            if user is not None:
                try:
                    account = Account.objects.get(numero=line["accountNumber"], owner=user)
                except Account.DoesNotExist:
                    raise serializers.ValidationError({"account": f"Account {line.get('accountNumber')} not found for this user."})
            else:
                account = Account.objects.get(numero=line["accountNumber"])

            tLine = TransactionLine(
                journal_entry=instance,
                account=account,
                accountNumber=account.numero,
                accountName=account.intitule,
                debit=line.get('debit') or 0,
                credit=line.get('credit') or 0,
                calculatedAmount=line.get('calculatedAmount') or 0,
                percentage=line.get('percentage') or 0,
                nature=line.get('nature')
            )

            tListObject.append(tLine)

        TransactionLine.objects.bulk_create(tListObject)
            

    return instance