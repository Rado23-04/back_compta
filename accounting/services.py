from typing import Dict, List, Any
from decimal import Decimal
from django.db import transaction
from .models import JournalEntry, Account, TransactionLine
from .utils import validate_entry

class JournalService:
    @staticmethod
    @transaction.atomic
    def create_journal_entry(data: Dict[str, Any]) -> JournalEntry:
        """Create a new journal entry with its transaction lines"""
        lines_data = data.pop('lines', [])
        
        # Validate the entry before saving
        validation_result = validate_entry(lines_data)
        if not validation_result['is_valid']:
            raise ValueError(validation_result['errors'])

        # Create the journal entry
        entry = JournalEntry.objects.create(**data)

        # Create transaction lines
        for line_data in lines_data:
            account_id = line_data.pop('account_id')
            account = Account.objects.get(id=account_id)
            TransactionLine.objects.create(
                journal_entry=entry,
                account=account,
                **line_data
            )

        return entry

    @staticmethod
    def get_balance_sheet(start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Calculate balance sheet for the specified period"""
        query = JournalEntry.objects.all()
        if start_date:
            query = query.filter(date__gte=start_date)
        if end_date:
            query = query.filter(date__lte=end_date)

        entries = query.prefetch_related('lines', 'lines__account')
        accounts = Account.objects.all()

        # Calculate totals
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        for entry in entries:
            for line in entry.lines.all():
                if line.debit:
                    total_debit += line.debit
                if line.credit:
                    total_credit += line.credit

        return {
            'entries': entries,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': total_debit - total_credit
        }

    @staticmethod
    def get_account_statement(account_id: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get account statement for the specified period"""
        account = Account.objects.get(id=account_id)
        query = JournalEntry.objects.filter(lines__account_id=account_id)
        
        if start_date:
            query = query.filter(date__gte=start_date)
        if end_date:
            query = query.filter(date__lte=end_date)

        entries = query.prefetch_related('lines').order_by('date')
        return entries