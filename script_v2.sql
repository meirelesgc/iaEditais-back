-- ==============================================================
-- 1. Tabela: test_collections (Agrupador de casos de teste)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.test_collections
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    description character varying COLLATE pg_catalog."default",
    
    -- Auditoria Padrão
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT test_collections_pkey PRIMARY KEY (id),
    CONSTRAINT fk_test_collections_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_collections_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_collections_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- ==============================================================
-- 2. Tabela: ai_models (Modelos de IA usados nas métricas)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.ai_models
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    code_name character varying COLLATE pg_catalog."default" NOT NULL,
    
    -- Auditoria Padrão
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT ai_models_pkey PRIMARY KEY (id),
    CONSTRAINT fk_ai_models_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_ai_models_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_ai_models_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- ==============================================================
-- 3. Tabela: metrics (Critérios de avaliação)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.metrics
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    -- model_id removido (agora é dinâmico na execução)
    criteria character varying COLLATE pg_catalog."default",
    evaluation_steps character varying COLLATE pg_catalog."default",
    threshold double precision,
    
    -- Auditoria Padrão
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT metrics_pkey PRIMARY KEY (id),
    CONSTRAINT fk_metrics_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_metrics_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_metrics_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- ==============================================================
-- 4. Tabela: test_cases (Cenários de teste)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.test_cases
(
    id uuid NOT NULL,
    test_collection_id uuid NOT NULL, -- Link com a coleção
    name character varying COLLATE pg_catalog."default" NOT NULL,
    branch_id uuid,
    doc_id uuid NOT NULL,
    input character varying COLLATE pg_catalog."default",
    expected_feedback character varying COLLATE pg_catalog."default",
    expected_fulfilled boolean NOT NULL,
    
    -- Auditoria Padrão
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT test_cases_pkey PRIMARY KEY (id),
    CONSTRAINT fk_test_cases_test_collection_id FOREIGN KEY (test_collection_id)
        REFERENCES public.test_collections (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_cases_branch_id FOREIGN KEY (branch_id)
        REFERENCES public.branches (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_cases_doc_id FOREIGN KEY (doc_id)
        REFERENCES public.documents (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_cases_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_cases_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_cases_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- ==============================================================
-- 5. Tabela: test_runs (O Evento de Execução)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.test_runs
(
    id uuid NOT NULL,
    test_collection_id uuid, -- Coleção que foi executada (opcional se for execução avulsa)
    
    -- Auditoria Padrão (created_at é a DATA DA EXECUÇÃO)
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT test_runs_pkey PRIMARY KEY (id),
    CONSTRAINT fk_test_runs_test_collection_id FOREIGN KEY (test_collection_id)
        REFERENCES public.test_collections (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_runs_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_runs_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_runs_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- ==============================================================
-- 6. Tabela: test_results (Os Resultados Detalhados)
-- ==============================================================
CREATE TABLE IF NOT EXISTS public.test_results
(
    id uuid NOT NULL,
    
    test_run_id uuid NOT NULL,  -- Link com o evento de execução
    test_case_id uuid NOT NULL, -- Link com o caso testado
    metric_id uuid NOT NULL,    -- Link com a métrica usada
    model_id uuid,              -- Link com o modelo usado na execução (opcional)
    
    threshold_used double precision,
    score_feedback double precision,
    passed_feedback boolean,
    reason_feedback character varying COLLATE pg_catalog."default",
    
    actual_feedback character varying COLLATE pg_catalog."default",
    actual_fulfilled boolean,
    passed_fulfilled boolean,
    
    -- Auditoria Padrão
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,

    CONSTRAINT test_results_pkey PRIMARY KEY (id),
    CONSTRAINT fk_test_results_test_run_id FOREIGN KEY (test_run_id)
        REFERENCES public.test_runs (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_test_case_id FOREIGN KEY (test_case_id)
        REFERENCES public.test_cases (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_metric_id FOREIGN KEY (metric_id)
        REFERENCES public.metrics (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_model_id FOREIGN KEY (model_id)
        REFERENCES public.ai_models (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_created_by FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_updated_by FOREIGN KEY (updated_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_test_results_deleted_by FOREIGN KEY (deleted_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);