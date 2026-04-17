-- Plan d'architecte : Exécuté une seule fois (Statique)
CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE checklist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_id UUID REFERENCES audits(id),
    requirement_id TEXT,
    description TEXT,
    criticality TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE non_conformities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id UUID REFERENCES checklist_items(id),
    description TEXT,
    severity TEXT,
    status TEXT DEFAULT 'open'
);
