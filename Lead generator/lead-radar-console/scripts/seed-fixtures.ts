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
  // Classification fixtures — ambiguous band (pre-score 0.40–0.75)
  {
    decisionId: '00000000-0000-0000-0000-000001000001',
    workflowId: 'signal_classification_ambiguous_band',
    profileVersion: 1,
    tierAtDecision: 'T1',
    inputsHash: 'fixture-c-001',
    inputsPayload: {
      in_ambiguous_band: true,
      signal: {
        source: 'ouders.nl forum',
        user: 'tweemoeders-bart',
        ageHours: 4,
        preScore: 0.62,
        postText: 'Even geleden post ik over de subsidie maar nog niet veel reactie. Iemand toch een idee wat zo\'n hybride installatie nu echt gaat kosten met de huidige aanvragen? Mijn aannemer wil offerte maar ik wil eerst beeld.',
      },
    },
    agentRecommendation: {
      candidates: [
        { categoryKey: 'research_intent', confidence: 0.62, reasoning: 'kostenvergelijking, geen koopintentie nu' },
        { categoryKey: 'purchase_intent_pre_quote', confidence: 0.28, reasoning: 'aannemer wil offerte uitbrengen → mogelijke buyer' },
        { categoryKey: 'no_intent', confidence: 0.10, reasoning: '' },
      ],
    },
    agentConfidence: 0.62,
    signalId: 'sig-c-001',
  },
  {
    decisionId: '00000000-0000-0000-0000-000001000002',
    workflowId: 'signal_classification_ambiguous_band',
    profileVersion: 1,
    tierAtDecision: 'T1',
    inputsHash: 'fixture-c-002',
    inputsPayload: {
      in_ambiguous_band: true,
      signal: {
        source: 'reddit r/zonnepanelen',
        user: 'solar_newbie_rdam',
        ageHours: 7,
        preScore: 0.55,
        postText: 'Heb net een huis gekocht in Rotterdam-Zuid, plat dak 45m2. Weet iemand of zonnepanelen op een plat dak renderen? Ik lees tegenstrijdige dingen over hoek en opbrengst.',
      },
    },
    agentRecommendation: {
      candidates: [
        { categoryKey: 'research_intent', confidence: 0.55, reasoning: 'technische vraag, oriëntatiefase' },
        { categoryKey: 'purchase_intent_pre_quote', confidence: 0.35, reasoning: 'nieuw huis, concreet dak → serieuze kandidaat' },
        { categoryKey: 'no_intent', confidence: 0.10, reasoning: '' },
      ],
    },
    agentConfidence: 0.55,
    signalId: 'sig-c-002',
  },
  {
    decisionId: '00000000-0000-0000-0000-000001000003',
    workflowId: 'signal_classification_ambiguous_band',
    profileVersion: 1,
    tierAtDecision: 'T2',
    inputsHash: 'fixture-c-003',
    inputsPayload: {
      in_ambiguous_band: true,
      signal: {
        source: 'tweakers.net forum',
        user: 'tweaker_duurzaam',
        ageHours: 2,
        preScore: 0.48,
        postText: 'Mijn buurman heeft een warmtepomp genomen van Vaillant. Ik vraag me af of die subsidie ISDE nog de moeite waard is na de recente bezuinigingen. Heeft iemand recent aangevraagd?',
      },
    },
    agentRecommendation: {
      candidates: [
        { categoryKey: 'research_intent', confidence: 0.52, reasoning: 'subsidie-informatie, geen directe koopuitdrukking' },
        { categoryKey: 'no_intent', confidence: 0.28, reasoning: 'louter informatievraag over beleid' },
        { categoryKey: 'purchase_intent_pre_quote', confidence: 0.20, reasoning: 'warmtepomp buurman → mogelijk zelf ook' },
      ],
    },
    agentConfidence: 0.52,
    signalId: 'sig-c-003',
  },
  {
    decisionId: '00000000-0000-0000-0000-000002000001',
    workflowId: 'conversion_registration', profileVersion: 1, tierAtDecision: 'T1',
    inputsHash: 'fixture-conv-001',
    inputsPayload: {
      outcome_confirmation_pending: true,
      history: { leadId: 'lead-7423', deliveredAt: '2026-05-01', installer: 'HVAC Schoonebeek BV', followupAt: '2026-05-15', repliedAt: '2026-05-16 14:32' },
      reply: '"Hi, klant heeft inderdaad bij ons getekend op 12 mei. Hybride lucht-water systeem, installatie staat gepland voor 15 juni. Bedrag: 14.500 incl BTW. Bedankt voor de doorverwijzing!"',
      parsed: { outcome: 'won', valueBand: '5-15k', install: 'likely', attribution: 'high' },
      parseConfidence: 0.94,
    },
    agentRecommendation: { parsedFields: { outcome: 'won', valueBand: '5-15k', install: 'likely', attribution: 'high' } },
    agentConfidence: 0.94, leadId: 'lead-7423',
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
