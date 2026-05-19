import { db } from './client';
import { operators, type Operator } from './schema';
import { eq } from 'drizzle-orm';

export async function getOperatorByEmail(email: string): Promise<Operator | undefined> {
  return db.query.operators.findFirst({ where: eq(operators.email, email) });
}

export async function getOperatorById(id: string): Promise<Operator | undefined> {
  return db.query.operators.findFirst({ where: eq(operators.operatorId, id) });
}

/** NEVER cache. Always re-derive from session. */
export async function requireCurrentOperator(): Promise<Operator> {
  const { auth } = await import('@/../auth');
  const session = await auth();
  if (!session?.user?.email) throw new Error('No active session');
  const op = await getOperatorByEmail(session.user.email);
  if (!op) throw new Error(`Session email not in operators: ${session.user.email}`);
  return op;
}
