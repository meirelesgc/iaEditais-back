CREATE TABLE IF NOT EXISTS public.tests
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    description character varying COLLATE pg_catalog."default",
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT tests_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.metrics
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    model_id uuid,
    criteria character varying COLLATE pg_catalog."default",
    evaluation_steps character varying COLLATE pg_catalog."default",
    threshold double precision,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT metrics_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.ai_models
(
    id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    code_name character varying COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT ai_models_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.test_cases
(
    id uuid NOT NULL,
    test_id uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    branch_id uuid,
    doc_id uuid NOT NULL,
    input character varying COLLATE pg_catalog."default",
    expected_feedback character varying COLLATE pg_catalog."default",
    expected_fulfilled boolean NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT test_cases_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.test_case_metrics
(
    id uuid NOT NULL,
    test_case_id uuid NOT NULL,
    metric_id uuid NOT NULL,
    test_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT test_case_metrics_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.test_runs
(
    id uuid NOT NULL,
    test_id uuid NOT NULL,
    created_by uuid,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT test_runs_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.test_run_cases
(
    id uuid NOT NULL,
    test_run_id uuid NOT NULL,
    test_case_metric_id uuid NOT NULL,
    test_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    CONSTRAINT test_run_cases_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.test_results
(
    id uuid NOT NULL,
    test_run_case_id uuid NOT NULL,
    model_id uuid,
    threshold_used double precision,
    reason_feedback character varying COLLATE pg_catalog."default",
    score_feedback double precision,
    passed_feedback boolean,
    actual_feedback character varying COLLATE pg_catalog."default",
    actual_fulfilled boolean,
    created_at timestamp without time zone NOT NULL DEFAULT now(),
    updated_at timestamp without time zone,
    deleted_at timestamp without time zone,
    created_by uuid,
    updated_by uuid,
    deleted_by uuid,
    passed_fulfilled boolean,
    CONSTRAINT test_results_pkey PRIMARY KEY (id)
)

