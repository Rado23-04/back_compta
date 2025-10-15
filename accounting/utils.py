
from .models import Account
from rest_framework import serializers

# Utility function to parse "compte" field into account number and name
def parse_compte(compte):

    try:
        numero, intitule = [s.strip() for s in compte.split(" - ", 1)]

    except Exception:
        raise serializers.ValidationError({"Transaction" :"Compte doit être: 'numero - intitule'"})
    
    return numero, intitule

# Utility function to parse incoming data for JournalEntry and its lines
def parse_data(data):

    accounts = []

    for line in data["lines"]:
        accounts.append(line.pop('account'))
    
    for account, line in zip(accounts, data["lines"]):
        try:
            account = Account.objects.get(pk=account)
            line['accountNumber'] = account.numero
            line['accountName'] = account.intitule
        except Account.DoesNotExist:
            raise serializers.ValidationError({'transactions': f'Le compte numero {account.numero}, intitulé {account.intitule} not found'})

    return data

# Utility function to check if the transactions are balanced and to validate account existence
def check_balance(lines):

    total_debit = sum((l.get('debit') or 0) for l in lines)
    total_credit = sum((l.get('credit') or 0) for l in lines)
    if round(total_debit - total_credit, 2) != 0:
        return False

    return True