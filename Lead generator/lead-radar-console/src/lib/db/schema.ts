import { pgTable, uuid, text, boolean, integer, timestamp, jsonb, real, pgEnum, index, uniqueIndex } from 'drizzle-orm/pg-core';

export const operatorRoleEnum = pgEnum('operator_role', ['operator', 'senior', 'lead']);

export const operators = pgTable('operators', {
  operatorId: uuid('operator_id').defaultRandom().primaryKey(),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
  role: operatorRoleEnum('role').notNull().default('operator'),
  active: boolean('active').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable('sessions', {
  sessionId: text('session_id').primaryKey(),
  operatorId: uuid('operator_id').notNull().references(() => operators.operatorId),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
  lastSeenAt: timestamp('last_seen_at', { withTimezone: true }).notNull().defaultNow(),
});

export const overrideCategories = pgTable('override_categories', {
  categoryKey: text('category_key').primaryKey(),
  displayLabel: text('display_label').notNull(),
  active: boolean('active').notNull().default(true),
  sortOrder: integer('sort_order').notNull().default(0),
  addedAt: timestamp('added_at', { withTimezone: true }).notNull().defaultNow(),
});

export const workflowProfiles = pgTable('workflow_profiles', {
  workflowId: text('workflow_id').notNull(),
  profileVersion: integer('profile_version').notNull(),
  profile: jsonb('profile').notNull(),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  createdBy: uuid('created_by').references(() => operators.operatorId),
}, (t) => ({
  pk: uniqueIndex('workflow_profiles_pk').on(t.workflowId, t.profileVersion),
}));

export const workflowKillState = pgTable('workflow_kill_state', {
  workflowId: text('workflow_id').primaryKey(),
  killedUntil: timestamp('killed_until', { withTimezone: true }),
  reason: text('reason').notNull(),
  setBy: uuid('set_by').notNull().references(() => operators.operatorId),
  setAt: timestamp('set_at', { withTimezone: true }).notNull().defaultNow(),
});

export const decisions = pgTable('decisions', {
  decisionId: uuid('decision_id').defaultRandom().primaryKey(),
  workflowId: text('workflow_id').notNull(),
  profileVersion: integer('profile_version').notNull(),
  tierAtDecision: text('tier_at_decision').notNull(),
  inputsHash: text('inputs_hash').notNull(),
  inputsPayload: jsonb('inputs_payload').notNull(),
  agentId: text('agent_id'),
  agentRecommendation: jsonb('agent_recommendation'),
  agentConfidence: real('agent_confidence'),
  agentReasoningRef: text('agent_reasoning_ref'),
  reviewerId: uuid('reviewer_id').references(() => operators.operatorId),
  reviewerDecision: jsonb('reviewer_decision'),
  agreement: text('agreement'),
  overrideReason: text('override_reason'),
  overrideCategory: text('override_category').references(() => overrideCategories.categoryKey),
  decidedAt: timestamp('decided_at', { withTimezone: true }).notNull().defaultNow(),
  timeToDecideMs: integer('time_to_decide_ms'),
  outcome: jsonb('outcome'),
  leadId: text('lead_id'),
  signalId: text('signal_id'),
}, (t) => ({
  workflowIdx: index('decisions_workflow_idx').on(t.workflowId, t.decidedAt),
  leadIdx: index('decisions_lead_idx').on(t.leadId),
  signalIdx: index('decisions_signal_idx').on(t.signalId),
  reviewerIdx: index('decisions_reviewer_idx').on(t.reviewerId),
}));

export const queueClaims = pgTable('queue_claims', {
  decisionId: uuid('decision_id').primaryKey().references(() => decisions.decisionId),
  claimedBy: uuid('claimed_by').notNull().references(() => operators.operatorId),
  claimedAt: timestamp('claimed_at', { withTimezone: true }).notNull().defaultNow(),
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
});

export type Operator = typeof operators.$inferSelect;
export type Decision = typeof decisions.$inferSelect;
export type WorkflowProfile = typeof workflowProfiles.$inferSelect;
