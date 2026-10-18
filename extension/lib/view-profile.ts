import {z} from 'zod'

export const viewType=z.enum(['header','inventory','detail','squad','dcp','objective','gallery','account','unknown'])
const selector=z.string().min(1).max(240)
// Configuration only. No scripts, dynamic expressions, arbitrary attributes or URLs.
export const viewProfile=z.object({
  profile_id:z.string().uuid(),revision:z.literal(1),edition:z.literal('FC27'),
  origin:z.string().url(),route:z.string().max(160),language:z.string().max(16),view:viewType,
  evidence_origin:z.enum(['local_region_map','observed_page_map']),map_id:z.string().uuid(),
  structure_hash:z.string().regex(/^[a-f0-9]{64}$/),status:z.literal('proposed'),
  recognition:z.array(selector).max(12),preconditions:z.array(z.string().max(120)).max(12),
  extractors:z.array(z.object({selector,field:z.string().max(60),normalization:z.enum(['text','integer','boolean','position']),
    required:z.boolean(),unique:z.boolean()}).strict()).max(30),
  loading_selectors:z.array(selector).max(8),uncertainties:z.array(z.string().max(160)).max(12),
  transitions:z.array(z.never()).max(0),extraction_enabled:z.literal(false),navigation_enabled:z.literal(false),
}).strict()
export type ViewProfile=z.infer<typeof viewProfile>
