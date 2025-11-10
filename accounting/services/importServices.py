
from django.db import transaction
from .journalEntryServices import create_journal_entry
from ..utils import parse_data, separate_dataframes
from rest_framework import serializers

def excel_to_database(df):

    with transaction.atomic():
        try:
            journalEntries = separate_dataframes(df, 'numeroEcriture')
            print(journalEntries)
            for _, journal_df in journalEntries.items():
                journal_data = {
                    "date": journal_df.iloc[0]['date'],
                    "libelle": journal_df.iloc[0]['libelle'],
                    "reference": journal_df.iloc[0]['reference'],
                    "numeroEcriture": journal_df.iloc[0]['numeroEcriture'],
                    "nature": journal_df.iloc[0]['nature'],
                    "lines": []
                }

                for _, row in journal_df.iterrows():
                    line_data = {
                        "account": row['account'],
                        "debit": row['debit'],
                        "credit": row['credit'],
                        "calculatedAmount": row['calculatedAmount'],
                        "percentage": row['percentage'],
                        "nature": row['lineNature']
                    }
                    journal_data["lines"].append(line_data)
                validated_data = parse_data(journal_data)
                create_journal_entry(validated_data)
        except Exception as e:
            raise serializers.ValidationError({"Import Error": str(e)})