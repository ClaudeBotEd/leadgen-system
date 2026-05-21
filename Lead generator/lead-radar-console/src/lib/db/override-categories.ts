import { db } from './client';
import { overrideCategories } from './schema';
import { eq, asc } from 'drizzle-orm';

export async function getActiveOverrideCategories() {
  return db.query.overrideCategories.findMany({
    where: eq(overrideCategories.active, true),
    orderBy: asc(overrideCategories.sortOrder),
  });
}
