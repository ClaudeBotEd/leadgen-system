import { db } from './client';
import { workflowKillState } from './schema';
import { eq, and, gt, isNull, or } from 'drizzle-orm';

export async function isWorkflowKilled(workflowId: string): Promise<boolean> {
  const row = await db.query.workflowKillState.findFirst({
    where: and(
      eq(workflowKillState.workflowId, workflowId),
      or(
        isNull(workflowKillState.killedUntil),
        gt(workflowKillState.killedUntil, new Date()),
      ),
    ),
  });
  return row != null;
}

export async function killWorkflow(
  workflowId: string,
  reason: string,
  setBy: string,
  durationMs?: number,
) {
  const killedUntil = durationMs ? new Date(Date.now() + durationMs) : null;
  await db
    .insert(workflowKillState)
    .values({ workflowId, reason, setBy, killedUntil })
    .onConflictDoUpdate({
      target: workflowKillState.workflowId,
      set: { reason, setBy, killedUntil, setAt: new Date() },
    });
}

export async function releaseWorkflowKill(workflowId: string) {
  await db.delete(workflowKillState).where(eq(workflowKillState.workflowId, workflowId));
}
