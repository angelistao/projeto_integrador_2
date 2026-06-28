-- Criação do banco e usuário
CREATE DATABASE estufa_db;
CREATE USER admin_estufa WITH ENCRYPTED PASSWORD 'estint123#';
GRANT ALL PRIVILEGES ON DATABASE estufa_db TO admin_estufa;

\c estufa_db

-- Tabela de configurações
CREATE TABLE configuracoes (
    id SERIAL PRIMARY KEY,
    nome_planta_pt VARCHAR(100),
    umidade_minima REAL,
    umidade_ideal REAL,
    info_cultivo_pt TEXT
);

INSERT INTO configuracoes (id) VALUES (1);

-- Tabela de histórico de leituras
CREATE TABLE leituras_sensores (
    id SERIAL PRIMARY KEY,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    umidade_solo REAL,
    temperatura REAL,
    caminho_foto VARCHAR(255)
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_estufa;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin_estufa;