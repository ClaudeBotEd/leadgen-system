CREATE TYPE "public"."operator_role" AS ENUM('operator', 'senior', 'lead');--> statement-breakpoint
CREATE TABLE "decisions" (
	"decision_id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"workflow_id" text NOT NULL,
	"profile_version" integer NOT NULL,
	"tier_at_decision" text NOT NULL,
	"inputs_hash" text NOT NULL,
	"inputs_payload" jsonb NOT NULL,
	"agent_id" text,
	"agent_recommendation" jsonb,
	"agent_confidence" real,
	"agent_reasoning_ref" text,
	"reviewer_id" uuid,
	"reviewer_decision" jsonb,
	"agreement" text,
	"override_reason" text,
	"override_category" text,
	"decided_at" timestamp with time zone DEFAULT now() NOT NULL,
	"time_to_decide_ms" integer,
	"outcome" jsonb,
	"lead_id" text,
	"signal_id" text
);
--> statement-breakpoint
CREATE TABLE "operators" (
	"operator_id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"email" text NOT NULL,
	"role" "operator_role" DEFAULT 'operator' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "operators_email_unique" UNIQUE("email")
);
--> statement-breakpoint
CREATE TABLE "override_categories" (
	"category_key" text PRIMARY KEY NOT NULL,
	"display_label" text NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"sort_order" integer DEFAULT 0 NOT NULL,
	"added_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "queue_claims" (
	"decision_id" uuid PRIMARY KEY NOT NULL,
	"claimed_by" uuid NOT NULL,
	"claimed_at" timestamp with time zone DEFAULT now() NOT NULL,
	"expires_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE "sessions" (
	"session_id" text PRIMARY KEY NOT NULL,
	"operator_id" uuid NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"last_seen_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "workflow_kill_state" (
	"workflow_id" text PRIMARY KEY NOT NULL,
	"killed_until" timestamp with time zone,
	"reason" text NOT NULL,
	"set_by" uuid NOT NULL,
	"set_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "workflow_profiles" (
	"workflow_id" text NOT NULL,
	"profile_version" integer NOT NULL,
	"profile" jsonb NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" uuid
);
--> statement-breakpoint
ALTER TABLE "decisions" ADD CONSTRAINT "decisions_reviewer_id_operators_operator_id_fk" FOREIGN KEY ("reviewer_id") REFERENCES "public"."operators"("operator_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "decisions" ADD CONSTRAINT "decisions_override_category_override_categories_category_key_fk" FOREIGN KEY ("override_category") REFERENCES "public"."override_categories"("category_key") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "queue_claims" ADD CONSTRAINT "queue_claims_decision_id_decisions_decision_id_fk" FOREIGN KEY ("decision_id") REFERENCES "public"."decisions"("decision_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "queue_claims" ADD CONSTRAINT "queue_claims_claimed_by_operators_operator_id_fk" FOREIGN KEY ("claimed_by") REFERENCES "public"."operators"("operator_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_operator_id_operators_operator_id_fk" FOREIGN KEY ("operator_id") REFERENCES "public"."operators"("operator_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "workflow_kill_state" ADD CONSTRAINT "workflow_kill_state_set_by_operators_operator_id_fk" FOREIGN KEY ("set_by") REFERENCES "public"."operators"("operator_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "workflow_profiles" ADD CONSTRAINT "workflow_profiles_created_by_operators_operator_id_fk" FOREIGN KEY ("created_by") REFERENCES "public"."operators"("operator_id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "decisions_workflow_idx" ON "decisions" USING btree ("workflow_id","decided_at");--> statement-breakpoint
CREATE INDEX "decisions_lead_idx" ON "decisions" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "decisions_signal_idx" ON "decisions" USING btree ("signal_id");--> statement-breakpoint
CREATE INDEX "decisions_reviewer_idx" ON "decisions" USING btree ("reviewer_id");--> statement-breakpoint
CREATE UNIQUE INDEX "workflow_profiles_pk" ON "workflow_profiles" USING btree ("workflow_id","profile_version");