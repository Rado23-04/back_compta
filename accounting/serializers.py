
from rest_framework import serializers
from .models import Account, JournalEntry, TransactionLine
from .services.journalEntryServices import create_journal_entry, update_journal_entry


# Serializer pour le modèle Account
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'numero', 'intitule', 'classe', 'type', 'nature', 'soldeInitial']

# Serializer minimal pour permettre uniquement la mise à jour de `soldeInitial`
class AccountSoldeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['soldeInitial']

# Serializer pour le modèle TransactionLine
class TransactionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionLine
        fields = ['id', 'accountNumber', 'accountName', 'debit', 'credit', 'calculatedAmount', 'percentage', 'nature']

# Serializer pour le modèle JournalEntry, incluant les lignes de transaction
class JournalEntrySerializer(serializers.ModelSerializer):
    lines = TransactionLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['id', 'date', 'libelle', 'reference', 'numeroEcriture', 'nature', 'created_at', 'updated_at', 'lines']

    def create(self, validated_data):
        # Pass the request user down to the service to ensure created objects are owned by the user
        user = None
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is not None:
            user = request.user

        return create_journal_entry(validated_data, user)

    def update(self, instance, validated_data):
        # Pass the request user so updates validate ownership
        user = None
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is not None:
            user = request.user

        return update_journal_entry(instance, validated_data, user)
    
    #engagement sociabilité


# Serializers pour l'import Excel
class ExcelImportLineSerializer(serializers.Serializer):
    date = serializers.CharField()
    reference = serializers.CharField(allow_blank=True, required=False)
    numeroEcriture = serializers.CharField()
    libelle = serializers.CharField()
    nature = serializers.CharField(allow_blank=True, required=False)
    account = serializers.CharField(allow_blank=True, required=False)
    accountName = serializers.CharField(allow_blank=True, required=False)
    debit = serializers.FloatField(required=False, default=0)
    credit = serializers.FloatField(required=False, default=0)
    calculatedAmount = serializers.FloatField(required=False, default=0)
    percentage = serializers.FloatField(required=False, default=0)
    lineNature = serializers.CharField(allow_blank=True, required=False)

    def to_internal_value(self, data):
        # Use parent to coerce fields, then normalize keys to expected names
        ret = super().to_internal_value(data)
        # Normalize keys
        normalized = {
            'date': ret.get('date'),
            'reference': ret.get('reference', ''),
            'numeroEcriture': ret.get('numeroEcriture'),
            'libelle': ret.get('libelle'),
            'nature': ret.get('nature', ''),
            'account': ret.get('account', ''),
            'accountName': ret.get('accountName', ''),
            'debit': ret.get('debit', 0) or 0,
            'credit': ret.get('credit', 0) or 0,
            'calculatedAmount': ret.get('calculatedAmount', 0) or 0,
            'percentage': ret.get('percentage', 0) or 0,
            'lineNature': ret.get('lineNature', ''),
        }
        return normalized


class ExcelImportSerializer(serializers.Serializer):
    lines = ExcelImportLineSerializer(many=True)

    def create(self, validated_data):
        # Create JournalEntry and TransactionLine objects grouped by (numeroEcriture, date, libelle)
        user = None
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is not None:
            user = request.user

        lines = validated_data.get('lines', [])
        # group
        groups = {}
        from django.utils import timezone
        for ln in lines:
            key = (ln['numeroEcriture'], ln['date'], ln['libelle'])
            groups.setdefault(key, []).append(ln)

        created_entries = []
        for (numeroEcriture, date, libelle), group_lines in groups.items():
            # take first line for reference and nature
            first = group_lines[0]
            je = JournalEntry(
                date=date,
                libelle=libelle,
                reference=first.get('reference') or '',
                numeroEcriture=numeroEcriture,
                nature=first.get('nature') or '',
            )
            # set ownership if model has owner
            if hasattr(je, 'owner') and user is not None:
                je.owner = user
            je.created_at = timezone.now()
            je.updated_at = timezone.now()
            je.save()

            tl_objs = []
            for item in group_lines:
                # try to find account by numero for this user
                acct = None
                acct_num = item.get('account') or ''
                if acct_num:
                    try:
                        acct = Account.objects.get(numero=str(acct_num), owner=user)
                    except Account.DoesNotExist:
                        acct = None

                tl = TransactionLine(
                    journal_entry=je,
                    account=acct,
                    accountNumber=acct_num or None,
                    accountName=item.get('accountName') or None,
                    debit=item.get('debit') or 0,
                    credit=item.get('credit') or 0,
                    calculatedAmount=item.get('calculatedAmount') or 0,
                    percentage=item.get('percentage') or 0,
                    nature=item.get('lineNature') or item.get('nature') or None,
                )
                tl_objs.append(tl)

            TransactionLine.objects.bulk_create(tl_objs)
            created_entries.append(je)

        return {'created_entries': len(created_entries)}


# Serializers for bulk JSON import
class BulkTransactionLineSerializer(serializers.Serializer):
    accountNumber = serializers.CharField(allow_blank=True, required=False)
    accountName = serializers.CharField(allow_blank=True, required=False)
    debit = serializers.FloatField(required=False, allow_null=True)
    credit = serializers.FloatField(required=False, allow_null=True)
    calculatedAmount = serializers.FloatField(required=False, allow_null=True)
    percentage = serializers.FloatField(required=False, allow_null=True)
    nature = serializers.CharField(allow_blank=True, required=False)

    def validate(self, data):
        debit = data.get('debit')
        credit = data.get('credit')
        if (debit is None or debit == 0) and (credit is None or credit == 0):
            raise serializers.ValidationError("Each line must have either debit or credit")
        return data


class BulkJournalEntrySerializer(serializers.Serializer):
    date = serializers.DateField()
    reference = serializers.CharField(allow_blank=True, required=False)
    numeroEcriture = serializers.CharField()
    libelle = serializers.CharField()
    nature = serializers.CharField(allow_blank=True, required=False)
    lines = BulkTransactionLineSerializer(many=True)

    def validate(self, data):
        # ensure lines present
        if not data.get('lines'):
            raise serializers.ValidationError({'lines': 'At least one transaction line is required.'})
        return data


class BulkImportSerializer(serializers.Serializer):
    entries = BulkJournalEntrySerializer(many=True)

    def create(self, validated_data):
        from django.utils import timezone
        created = []
        user = None
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is not None:
            user = request.user

        entries = validated_data.get('entries', [])
        for entry in entries:
            numero = entry.get('numeroEcriture')
            date = entry.get('date')
            # duplicate check
            if JournalEntry.objects.filter(numeroEcriture=numero, date=date).exists():
                # signal duplicate by raising a special ValidationError
                raise serializers.ValidationError({'detail': f'Duplicate entry for numeroEcriture {numero} and date {date}.'})

            je = JournalEntry(
                date=date,
                libelle=entry.get('libelle'),
                reference=entry.get('reference') or '',
                numeroEcriture=numero,
                nature=entry.get('nature') or '',
            )
            if hasattr(je, 'owner') and user is not None:
                je.owner = user
            je.created_at = timezone.now()
            je.updated_at = timezone.now()
            je.save()

            tlines = []
            for ln in entry.get('lines', []):
                acct = None
                acct_num = ln.get('accountNumber')
                if acct_num:
                    try:
                        acct = Account.objects.get(numero=str(acct_num), owner=user)
                    except Account.DoesNotExist:
                        acct = None

                tl = TransactionLine(
                    journal_entry=je,
                    account=acct,
                    accountNumber=acct_num or None,
                    accountName=ln.get('accountName') or None,
                    debit=ln.get('debit') or 0,
                    credit=ln.get('credit') or 0,
                    calculatedAmount=ln.get('calculatedAmount') or 0,
                    percentage=ln.get('percentage') or 0,
                    nature=ln.get('nature') or None,
                )
                tlines.append(tl)

            TransactionLine.objects.bulk_create(tlines)
            created.append(je)

        return {'created_count': len(created), 'entries': created}