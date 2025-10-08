from rest_framework import serializers
from .models import Account, JournalEntry, TransactionLine

# Serializer pour le modèle Account
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'numero', 'intitule', 'classe', 'type', 'nature', 'soldeInitial']

# Serializer pour le modèle TransactionLine
class TransactionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionLine
        fields = ['id', 'compte', 'accountNumber', 'accountName', 'debit', 'credit', 'calculatedAmount', 'percentage', 'nature']

# Serializer pour le modèle JournalEntry, incluant les lignes de transaction
class JournalEntrySerializer(serializers.ModelSerializer):
    lines = TransactionLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ['id', 'date', 'libelle', 'reference', 'numeroEcriture', 'nature', 'created_at', 'updated_at', 'lines']

    def create(self, validated_data):
        # Création d'une écriture avec ses lignes
        lines_data = validated_data.pop('lines')
        entry = JournalEntry.objects.create(**validated_data)
        for line_data in lines_data:
            compte = line_data.pop('compte')
            accountNumber = compte.split(" - ")[0]
            accountName = compte.split(" - ")[1]
            account = Account.objects.get(numero=accountNumber)
            TransactionLine.objects.create(journal_entry=entry,account=account,accountNumber=accountNumber,accountName=accountName,**line_data)
        return entry
