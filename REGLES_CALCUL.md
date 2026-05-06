# Règles de calcul — Dashboard AGECA

## Sources de données

| Fichier | Rôle |
|---------|------|
| `csv/export_roomingit.csv` | Export RoomingIT — source principale (1 495 lignes) |
| `csv/liste_contact.csv` | Annuaire clients avec catégorie tarifaire (Zone6) |
| `csv/reconciliaton_nassima.csv` | Journal comptable double-entrée pour réconciliation |

---

## Structure d'`export_roomingit.csv`

Chaque ligne est une **option/service** d'une réservation. Une même réservation (même `N° de document`) peut avoir plusieurs lignes.

| Colonne CSV | Colonne DB | Description |
|-------------|------------|-------------|
| Date de réservation | `reservation_date` | Date d'utilisation de la salle |
| Date de document | `doc_date` | Date d'émission de la facture/avoir |
| Statut | `status` | Cycle de vie : Posée / Confirmée / Facturée / Encaissée / Annulée |
| Type de document | `doc_type` | Devis / Facture / Avoir |
| N° de document | `doc_number` | Référence du document (F=Facture, A=Avoir, D=Devis) |
| Prix HT | `price_ht` | Prix hors taxes |
| Taux de TVA | `tva_rate` | Taux TVA (généralement 0 % pour les associations) |
| Prix TTC | `price_ttc` | Prix toutes taxes comprises |
| Quantité | `quantity` | Quantité |
| Compte comptable | `gl_account` | Compte de produit (70xxx) |
| Type d'option | `option_type` | Catégorie tarifaire (CAT 1-4, EPN, LE 86, Matériel, Services) |
| N° de l'organisateur | `organizer_id` | Clé contact (lien vers `liste_contact.csv`) |

---

## Cycle de vie d'une réservation

```
Posée → Confirmée → Facturée → Encaissée
                 ↘ Annulée
```

- **Posée / Confirmée** : pas encore de document de facturation émis
- **Facturée** : facture émise, paiement non reçu
- **Encaissée** : facture émise ET paiement reçu
- **Annulée** : peut être associée à un Devis, une Facture ou un Avoir

---

## Règles de calcul du CA

### CA Brut (Chiffre d'affaires facturé TTC)

```sql
SUM(CASE WHEN doc_type = 'Facture' THEN price_ttc * quantity ELSE 0 END)
- SUM(CASE WHEN doc_type = 'Avoir'   THEN price_ttc * quantity ELSE 0 END)
```

- Inclut toutes les factures (Facturée + Encaissée)
- Déduit les avoirs (remboursements / annulations avec remboursement)
- **Exclut** les Devis (simples propositions commerciales)

### CA Net (Chiffre d'affaires encaissé TTC)

```sql
SUM(CASE WHEN doc_type = 'Facture' AND status = 'Encaissée'
         THEN price_ttc * quantity ELSE 0 END)
```

- Uniquement les factures dont le paiement a été reçu
- Les avoirs ne s'appliquent pas ici (l'encaissement est déjà net)

### Écart (non encaissé)

```
Écart = CA Brut - CA Net
```

Montant facturé mais pas encore reçu en caisse.

---

## Comptage des réservations

```sql
COUNT(DISTINCT doc_number)
```

Filtré par **`reservation_date`** (date d'utilisation de la salle), pas par `doc_date`.

> ⚠️ Le CA est calculé sur `doc_date` (date de facturation), le nombre de réservations sur `reservation_date` (date d'usage). Un filtre sur une période donnée peut donc donner des résultats apparemment asymétriques entre les deux métriques.

---

## Totaux sur les données actuelles du CSV

| Indicateur | Valeur |
|------------|--------|
| CA Brut (Factures − Avoirs) | **114 502 €** |
| CA Net (Encaissé seulement) | **91 755 €** |
| Écart (non encaissé) | **22 747 €** |

---

## Plan comptable — Comptes de produit (70x)

### Salles de réunion (petites — 19 places)

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70111 | CAT 1 | Salles 19 places — 1/2 journée |
| 70112 | CAT 2 | Salles 19 places — journée / 1/2 journée |
| 70113 | CAT 3 | Salles 19 places — journée / 1/2 journée |
| 70114 | CAT 4 | Salles 19 places — 1/2 journée |
| 70153 | CAT 3 | Salle Visio 19 places — journée / 1/2 journée |

### Salle 7 (70 places)

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70121 | CAT 1 | Salle 7 — 1/2 journée |
| 70122 | CAT 2 | Salle 7 — journée / 1/2 journée |
| 70123 | CAT 3 | Salle 7 — journée / 1/2 journée |

### Salle 8 (35 places)

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70161 | CAT 1 | Salle 8 — 1/2 journée |
| 70162 | CAT 2 | Salle 8 — journée / 1/2 journée |
| 70163 | CAT 3 | Salle 8 — journée / 1/2 journée |

### Salle 9 (175 places)

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70131 | CAT 1 | Salle 9 — journée / 1/2 journée |
| 70132 | CAT 2 | Salle 9 — journée |
| 70133 | CAT 3 | Salle 9 — journée / 1/2 journée |
| 70134 | CAT 4 | Salle 9 — 1/2 journée |

### Autres espaces

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70171 | LE 86 | Annexe — journée / 1/2 journée / soirée |
| 70183 | CAT 3 | Espace convivial, Tout l'AGECA |
| 7021 | Salle multimédia | Salle multimédia — 1/2 journée |

### Adhésions

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 7001 | CAT 1 | Adhésion |
| 7002 | CAT 2 | Adhésion |
| 7003 | CAT 3 | Adhésion |
| 70041 | EPN | Adhésion EPN |

### Matériel et services

| Compte | Catégorie | Description |
|--------|-----------|-------------|
| 70952 | Matériel | Forfait Vidéoprojecteur (journée / 1/2 journée) |
| 7096 | Matériel | Paperboard |
| 70822 | Services | Supplément ménage grande salle |
| 7091 | Services | Photocopie A4 |
| 7098 | Services | AGECAFE |

---

## Catégories tarifaires (Zone6 dans `liste_contact.csv`)

La Zone6 du contact définit le tarif appliqué lors de ses réservations.

| Zone6 | Nombre de contacts | Correspond à `Type d'option` |
|-------|--------------------|------------------------------|
| Cat. 1 | 751 | CAT 1 |
| Cat. 2 | 370 | CAT 2 |
| Cat. 3 | 2 584 | CAT 3 (le plus courant) |
| Cat. 4 | 385 | CAT 4 |
| Cat. 5 | 1 161 | *(non présent dans les options — cf. note ci-dessous)* |
| Prospect | 19 | — |

> ⚠️ La **Cat. 5** existe dans `liste_contact.csv` mais n'apparaît pas en tant que `Type d'option` dans les réservations. Les contacts Cat. 5 semblent être facturés selon une autre catégorie (probablement CAT 4 ou une facturation spécifique).

La **Zone5** correspond à l'année d'adhésion active du contact (2022 – 2026).

Le lien entre `export_roomingit.csv` et `liste_contact.csv` :
```
N° de l'organisateur (clecontact)  ←→  CleContact
```

---

## Réconciliation comptable (`reconciliaton_nassima.csv`)

Journal comptable en double entrée. Chaque document apparaît sur plusieurs lignes.

### Journal VTE (ventes) — Émission facture

| Sens | Compte | Signification |
|------|--------|---------------|
| Débit | 411xxxxx | Créance client (montant dû) |
| Crédit | 70xxx | Produit (CA reconnu) |

### Journal OD (opérations diverses) — Encaissement

| Sens | Compte | Signification |
|------|--------|---------------|
| Débit | 51223 | Banque (argent reçu) |
| Crédit | 411xxxxx | Solde la créance client |

### Journal VTE — Avoir (remboursement)

| Sens | Compte | Signification |
|------|--------|---------------|
| Débit | 70xxx | Annulation du produit |
| Crédit | 411xxxxx | Avoir dû au client |

### Lien avec les contacts

```
Compte 411 dans le journal  →  supprimer le préfixe "411"  →  CleContact dans liste_contact.csv
Exemple : compte 41113917  →  clecontact = 13917
```

---

## Cas particuliers à connaître

| Cas | Comportement |
|-----|-------------|
| Annulée + Devis | Pas de document financier émis, exclus du CA |
| Annulée + Facture | Facture comptabilisée dans CA Brut jusqu'à émission d'un avoir |
| Annulée + Avoir | L'avoir déduit la facture dans le CA Brut |
| Confirmée sans document | Non comptabilisée dans le CA (pas encore de facture) |
| Facturée + Facture | Dans CA Brut uniquement (pas dans CA Net) |
| Encaissée + Facture | Dans CA Brut **et** CA Net |
| Encaissée + Devis | Anomalie possible — pas comptabilisée dans le CA |
