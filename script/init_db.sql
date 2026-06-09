-- init_db.sql
CREATE TABLE IF NOT EXISTS comptes (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,  -- Ex: "Actif", "Passif", "Charges", "Produits"
    solde DECIMAL(15, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exemple d'insertion de données (optionnel)
INSERT INTO comptes (numero, nom, type, solde)
VALUES
    ('512', 'Compte courant', 'Actif', 1500.00),
    ('401', 'Fournisseurs', 'Passif', 0.00),
    ('606', 'Achats de marchandises', 'Charges', 0.00),
    ('706', 'Ventes de marchandises', 'Produits', 0.00)
ON CONFLICT (numero) DO NOTHING;
