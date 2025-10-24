
from rest_framework import serializers
from .models import Account, JournalEntry, TransactionLine
from .services.journalEntryServices import create_journal_entry, update_journal_entry


# Serializer pour le modèle Account
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'numero', 'intitule', 'classe', 'type', 'nature', 'soldeInitial']

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

        return create_journal_entry(validated_data)

    def update(self, instance, validated_data):
        
        return update_journal_entry(instance, validated_data)
    
class ImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith(('.xls', '.xlsx', 'csv')):
            raise serializers.ValidationError("Le fichier doit être au format Excel (.xls ou .xlsx ou .csv).")
        return value