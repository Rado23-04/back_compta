
from django.db import models

# Modèle Django pour un compte comptable
class Account(models.Model):
	numero = models.CharField(max_length=20)  # Numéro de compte (ex: 411000)
	intitule = models.CharField(max_length=100)  # Intitulé du compte
	classe = models.IntegerField()  # Classe comptable (1 à 8)
	TYPE_CHOICES = [
		('Actif', 'Actif'),
		('Passif', 'Passif'),
		('Charge', 'Charge'),
		('Produit', 'Produit'),
		('TVA', 'TVA'),
		('Autre', 'Autre'),
	]
	type = models.CharField(max_length=20, choices=TYPE_CHOICES)  # Type de compte
	nature = models.CharField(max_length=100, blank=True, null=True)  # Nature (optionnel)
	solde_initial = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Solde initial

	def __str__(self):
		return f"{self.numero} - {self.intitule}"

# Modèle Django pour une écriture comptable (JournalEntry)
class JournalEntry(models.Model):
	date = models.DateField()  # Date de l'écriture
	libelle = models.CharField(max_length=200)  # Libellé de l'opération
	reference = models.CharField(max_length=100, blank=True, null=True)  # Référence (optionnel)
	numero_ecriture = models.CharField(max_length=50)  # Numéro d'écriture
	nature = models.CharField(max_length=100, blank=True, null=True)  # Nature de l'opération (optionnel)
	created_at = models.DateTimeField(auto_now_add=True)  # Date de création
	updated_at = models.DateTimeField(auto_now=True)  # Date de modification

	def __str__(self):
		return f"{self.numero_ecriture} - {self.libelle}"

# Modèle Django pour une ligne de transaction liée à une écriture et un compte
class TransactionLine(models.Model):
	journal_entry = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)  # Lien vers l'écriture
	account = models.ForeignKey(Account, on_delete=models.PROTECT)  # Lien vers le compte
	debit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # Montant débit
	credit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # Montant crédit
	calculated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Montant calculé
	percentage = models.FloatField(default=0)  # Pourcentage
	nature = models.CharField(max_length=100, blank=True, null=True)  # Nature (optionnel)

	def __str__(self):
		return f"Ligne {self.id} - Compte {self.account.numero}"

# Create your models here.
