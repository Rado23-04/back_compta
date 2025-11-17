
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