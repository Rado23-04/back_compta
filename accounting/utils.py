from decimal import Decimal
from typing import List, Dict, Any
from .models import Account, JournalEntry, TransactionLine

def calculate_vat_amount(amount: Decimal, vat_percent: Decimal) -> Decimal:
    return (amount * vat_percent) / Decimal('100')

def calculate_ht_from_ttc(ttc_amount: Decimal, vat_percent: Decimal) -> Decimal:
    return ttc_amount / (Decimal('1') + vat_percent / Decimal('100'))

def calculate_ttc_from_ht(ht_amount: Decimal, vat_percent: Decimal) -> Decimal:
    return ht_amount * (Decimal('1') + vat_percent / Decimal('100'))

def calculate_balance(entries: List[JournalEntry], accounts: List[Account]) -> List[Dict[str, Any]]:
    balance_map = {}

    # Initialize with accounts
    for account in accounts:
        balance_map[account.id] = {
            'account_id': account.id,
            'account_number': account.numero,
            'account_name': account.intitule,
            'total_debit': account.solde_initial if account.solde_initial > 0 else 0,
            'total_credit': abs(account.solde_initial) if account.solde_initial < 0 else 0,
            'solde': account.solde_initial,
            'type': 'debiteur' if account.solde_initial >= 0 else 'crediteur'
        }

    # Calculate totals from entries
    for entry in entries:
        for line in entry.lines.all():
            balance = balance_map.get(line.account.id)
            if balance:
                if line.debit:
                    balance['total_debit'] += line.debit
                    balance['solde'] += line.debit
                if line.credit:
                    balance['total_credit'] += line.credit
                    balance['solde'] -= line.credit
                balance['type'] = 'debiteur' if balance['solde'] >= 0 else 'crediteur'

    return list(balance_map.values())

def calculate_account_balance(account: Account, entries: List[JournalEntry]) -> List[Dict[str, Any]]:
    movements = []
    current_balance = account.solde_initial

    # Sort entries by date
    entries_with_account = [
        entry for entry in entries 
        if entry.lines.filter(account=account).exists()
    ]
    sorted_entries = sorted(entries_with_account, key=lambda x: x.date)

    for entry in sorted_entries:
        for line in entry.lines.filter(account=account):
            if line.debit:
                current_balance += line.debit
            if line.credit:
                current_balance -= line.credit

            movements.append({
                'date': entry.date.isoformat(),
                'numero_ecriture': entry.numero_ecriture,
                'libelle': entry.libelle,
                'reference': entry.reference,
                'debit': line.debit,
                'credit': line.credit,
                'solde': current_balance
            })

    return movements

def validate_entry(lines: List[Dict]) -> Dict[str, Any]:
    errors = []
    
    if not lines:
        errors.append('Au moins une ligne est requise')
        return {'is_valid': False, 'errors': errors}

    total_debit = sum(Decimal(str(line.get('debit', 0) or 0)) for line in lines)
    total_credit = sum(Decimal(str(line.get('credit', 0) or 0)) for line in lines)

    if abs(total_debit - total_credit) > Decimal('0.01'):
        errors.append(f"L'écriture n'est pas équilibrée. Débit: {total_debit}, Crédit: {total_credit}")

    for i, line in enumerate(lines):
        if not line.get('account_id'):
            errors.append(f'Le compte est requis pour la ligne {i + 1}')
        if not line.get('debit') and not line.get('credit'):
            errors.append(f'Un montant débit ou crédit est requis pour la ligne {i + 1}')
        if line.get('debit') and line.get('credit'):
            errors.append(f'Une ligne ne peut pas avoir à la fois un débit et un crédit (ligne {i + 1})')

    return {'is_valid': len(errors) == 0, 'errors': errors}