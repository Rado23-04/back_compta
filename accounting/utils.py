
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

    comptes = []

    for line in data["lines"]:
        comptes.append(line.pop('compte'))
    
    for compte, line in zip(comptes, data["lines"]):
        numero, intitule = parse_compte(compte)
        line['accountNumber'] = numero
        line['accountName'] = intitule

    return data

# Utility function to check if the transactions are balanced and to validate account existence
def check_balance(lines):

    total_debit = sum((l.get('debit') or 0) for l in lines)
    total_credit = sum((l.get('credit') or 0) for l in lines)
    if round(total_debit - total_credit, 2) != 0:
        return False

    return True

# Utility function to validate and retrieve an Account instance
def check_get_account(account_num, account_name, idx):

    try:
        account = Account.objects.get(numero=account_num)

    except Account.DoesNotExist:
        raise serializers.ValidationError({'transactions': {idx: f'Le compte numero {account_num}, intitulé {account_name} not found'}})

    return account