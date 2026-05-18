import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';

const fixtures = [
  {
    decisionId: '00000000-0000-0000-0000-000000000001',
    workflowId: 'lead_delivery_routing',
    profileVersion: 1,
    tierAtDecision: 'T1',
    inputsHash: 'fixture-r-001',
    inputsPayload: {
      lead: {
        score: 87,
        band: 'HOT',
        source: 'tweakers',
        ageHours: 2,
        niche: 'warmtepomp',
        geo: { region: 'Drenthe', city: 'Schoonebeek', postcode: '7741' },
        postText: 'We willen onze gasketel vervangen, hebben offerte van XYZ gekregen maar willen tweede mening. Iemand recente ervaring met hybride lucht-water systemen in deze regio?',
      },
    },
    agentRecommendation: {
      primary: {
        name: 'HVAC Schoonebeek BV',
        regionalFit: 'strong',
        conversionHistory: 'high',
        capacity: 'open',
        nicheMatch: 'hybrid-specialized',
        responseHistory: 'responsive',
        distanceKm: 8,
      },
      alternatives: [
        {
          name: 'Klima-Tech Drenthe',
          regionalFit: 'moderate',
          conversionHistory: 'solid',
          capacity: 'tight',
          nicheMatch: 'generalist',
          responseHistory: 'responsive',
          distanceKm: 12,
        },
        {
          name: 'NoordWarmte BV',
          regionalFit: 'distance_limit',
          conversionHistory: 'limited',
          capacity: 'limited',
          nicheMatch: 'generalist',
          responseHistory: 'slow',
          distanceKm: 18,
        },
      ],
    },
    agentConfidence: 0.85,
    leadId: 'lead-fixture-001',
  },
  {
    decisionId: '00000000-0000-0000-0000-000000000002',
    workflowId: 'lead_delivery_routing',
    profileVersion: 1,
    tierAtDecision: 'T2',
    inputsHash: 'fixture-r-002',
    inputsPayload: {
      lead: {
        score: 65,
        band: 'WARM',
        source: 'marktplaats',
        ageHours: 5,
        niche: 'airco',
        geo: { region: 'Friesland', city: 'Leeuwarden', postcode: '8911' },
        postText: 'Op zoek naar installateur voor airconditioning in woonhuis. Hebben een offerte nodig voor ruimte van 40m2. Graag reactie van gespecialiseerde bedrijven.',
      },
    },
    agentRecommendation: {
      primary: {
        name: 'Climate Control Friesland',
        regionalFit: 'strong',
        conversionHistory: 'high',
        capacity: 'open',
        nicheMatch: 'airco-specialist',
        responseHistory: 'responsive',
        distanceKm: 5,
      },
      alternatives: [
        {
          name: 'AirTech Nederland',
          regionalFit: 'moderate',
          conversionHistory: 'moderate',
          capacity: 'open',
          nicheMatch: 'generalist',
          responseHistory: 'responsive',
          distanceKm: 15,
        },
        {
          name: 'Cool Solutions BV',
          regionalFit: 'distance_limit',
          conversionHistory: 'limited',
          capacity: 'tight',
          nicheMatch: 'generalist',
          responseHistory: 'slow',
          distanceKm: 22,
        },
      ],
    },
    agentConfidence: 0.72,
    leadId: 'lead-fixture-002',
  },
  {
    decisionId: '00000000-0000-0000-0000-000000000003',
    workflowId: 'lead_delivery_routing',
    profileVersion: 1,
    tierAtDecision: 'T1',
    inputsHash: 'fixture-r-003',
    inputsPayload: {
      lead: {
        score: 92,
        band: 'HOT',
        source: 'zonnepanelen.org',
        ageHours: 1,
        niche: 'zonnepanelen',
        geo: { region: 'Limburg', city: 'Roggel', postcode: '6088' },
        postText: 'Interesse in zonnepanelen voor dak van woning. Elektrisch verbruik gemiddeld 5000 kWh per jaar. Willen graag 3 offertes vergelijken van erkende installateurs in buurt.',
      },
    },
    agentRecommendation: {
      primary: {
        name: 'Solartech Limburg',
        regionalFit: 'strong',
        conversionHistory: 'high',
        capacity: 'open',
        nicheMatch: 'solar-expert',
        responseHistory: 'very-responsive',
        distanceKm: 3,
      },
      alternatives: [
        {
          name: 'Zonnegroep Maastricht',
          regionalFit: 'strong',
          conversionHistory: 'high',
          capacity: 'open',
          nicheMatch: 'solar-expert',
          responseHistory: 'responsive',
          distanceKm: 12,
        },
        {
          name: 'Green Energy Solutions',
          regionalFit: 'moderate',
          conversionHistory: 'solid',
          capacity: 'tight',
          nicheMatch: 'generalist',
          responseHistory: 'responsive',
          distanceKm: 25,
        },
      ],
    },
    agentConfidence: 0.91,
    leadId: 'lead-fixture-003',
  },
];

async function main() {
  await db.insert(decisions).values(fixtures).onConflictDoNothing();
  console.log(`✓ Seeded ${fixtures.length} fixtures`);
  await sql.end();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
