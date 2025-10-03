from rest_framework import serializers
from .models import Account, JournalEntry, TransactionLine

# Serializer pour le modèle Account
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'numero', 'intitule', 'classe', 'type', 'nature', 'solde_initial']
 
# Serializer pour le modèle TransactionLine
class TransactionLineSerializer(serializers.ModelSerializer):
    account = AccountSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all(), source='account', write_only=True)

    class Meta:
        model = TransactionLine
        fields = ['id', 'account', 'account_id', 'debit', 'credit', 'calculated_amount', 'percentage', 'nature']

# Serializer pour le modèle JournalEntry, incluant les lignes de transaction
class JournalEntrySerializer(serializers.ModelSerializer):
    lines = TransactionLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['id', 'date', 'libelle', 'reference', 'numero_ecriture', 'nature', 'created_at', 'updated_at', 'lines']

    def create(self, validated_data):
        # Création d'une écriture avec ses lignes
        lines_data = validated_data.pop('lines')
        entry = JournalEntry.objects.create(**validated_data)
        for line_data in lines_data:
            account = line_data.pop('account') if 'account' in line_data else None
            TransactionLine.objects.create(journal_entry=entry, **line_data)
        return entry
