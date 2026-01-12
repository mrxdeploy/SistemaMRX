-- Adicionar colunas relacionadas ao sistema de tabelas de preço
-- Execução segura: adiciona apenas se não existir

DO $$
BEGIN
    -- Coluna para status da tabela de preço
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'fornecedores' 
        AND column_name = 'tabela_preco_status'
    ) THEN
        ALTER TABLE fornecedores 
        ADD COLUMN tabela_preco_status VARCHAR(20) DEFAULT 'pendente';
    END IF;

    -- Coluna para data de aprovação da tabela
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'fornecedores' 
        AND column_name = 'tabela_preco_aprovada_em'
    ) THEN
        ALTER TABLE fornecedores 
        ADD COLUMN tabela_preco_aprovada_em TIMESTAMP;
    END IF;

    -- Coluna para quem aprovou a tabela
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'fornecedores' 
        AND column_name = 'tabela_preco_aprovada_por_id'
    ) THEN
        ALTER TABLE fornecedores 
        ADD COLUMN tabela_preco_aprovada_por_id INTEGER REFERENCES usuarios(id);
    END IF;
END $$;

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_fornecedores_tabela_preco_status 
ON fornecedores(tabela_preco_status);

CREATE INDEX IF NOT EXISTS idx_fornecedores_tabela_preco_aprovada_por 
ON fornecedores(tabela_preco_aprovada_por_id);