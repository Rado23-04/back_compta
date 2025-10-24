
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
            raise serializers.ValidationError({'transactions': f'Le compte est introuvable'})

    return data

# Utility function to check if the transactions are balanced and to validate account existence
def check_balance(lines):

    total_debit = sum((l.get('debit') or 0) for l in lines)
    total_credit = sum((l.get('credit') or 0) for l in lines)
    if round(total_debit - total_credit, 2) != 0:
        return False

    return True

# Utility function to update an account's soldeInitial based on debit and credit amounts
"""
def update_account_solde(account_id, debit, credit):

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        raise serializers.ValidationError({'transactions': f'Le compte est introuvable'})

    if debit < 0 or credit < 0:
        raise serializers.ValidationError({'transactions': f'Les montants débit et crédit doivent être positifs'})

    account.soldeInitial += (debit - credit)
    account.save()

    return account
"""

def separate_dataframes(df, group_column):
    """Separate DataFrame into individual DataFrames for each group value"""
    grouped = df.groupby(group_column)
    separated_dfs = {}
    
    for value, group_df in grouped:
        # Create variable name
        var_name = f"df_{value}"
        separated_dfs[var_name] = group_df.reset_index(drop=True)
        
        # Also create actual variables (use with caution)
        globals()[var_name] = group_df.reset_index(drop=True)
    
    return separated_dfs