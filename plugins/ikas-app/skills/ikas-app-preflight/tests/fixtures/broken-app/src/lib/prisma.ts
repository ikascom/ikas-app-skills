import { PrismaClient } from '@prisma/client';

// Avoid creating multiple PrismaClient instances in development (Next.js hot reload)
const globalForPrisma = global as unknown as { prisma: PrismaClient | undefined };

export const prisma: PrismaClient =
  globalForPrisma.prisma ?? new PrismaClient({});

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}


