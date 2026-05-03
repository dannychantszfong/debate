import React from 'react';
import {
	AbsoluteFill,
	Html5Audio,
	interpolate,
	spring,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {z} from 'zod';

const speakerSchema = z.string().min(1);
const speakerSideSchema = z.enum(['left', 'right', 'center']);
export const debateLayoutSchema = z.enum(['dual', 'podcast', 'mindmap']);

const debateTurnSchema = z.object({
	turn: z.number(),
	speaker: speakerSchema,
	start: z.number(),
	end: z.number(),
	duration: z.number().optional(),
	content: z.string(),
});

const debateSegmentSchema = z.object({
	turn: z.number(),
	speaker: speakerSchema,
	text: z.string(),
	start: z.number(),
	end: z.number(),
	accepted: z.boolean().optional(),
});

export const debateTimelineSchema = z.object({
	duration: z.number().positive(),
	turns: z.array(debateTurnSchema).min(1),
	segments: z.array(debateSegmentSchema).min(1),
});

const videoPlanCastSchema = z.object({
	id: speakerSchema,
	displayName: z.string().optional(),
	role: z.enum(['host', 'debater', 'moderator', 'guest']).optional(),
	side: speakerSideSchema.optional(),
	accent: z.string().optional(),
	avatarLabel: z.string().optional(),
	avatarImage: z.string().optional(),
});

const videoPlanChapterSchema = z.object({
	id: z.string().min(1),
	label: z.string().min(1),
	start: z.number().nonnegative(),
	end: z.number().positive().optional(),
});

const videoPlanClaimSchema = z.object({
	id: z.string().min(1),
	speaker: speakerSchema,
	turn: z.number().optional(),
	start: z.number().nonnegative(),
	end: z.number().positive().optional(),
	summary: z.string().min(1),
	type: z
		.enum(['claim', 'rebuttal', 'question', 'moderation', 'closing'])
		.optional(),
	topic: z.string().optional(),
	evidenceIds: z.array(z.string()).optional(),
	targets: z.array(z.string()).optional(),
});

const videoPlanEvidenceSchema = z.object({
	id: z.string().min(1),
	claimId: z.string().optional(),
	start: z.number().nonnegative(),
	end: z.number().positive().optional(),
	label: z.string().min(1),
	summary: z.string().min(1),
	kind: z.enum(['support', 'example', 'data', 'context', 'flagged']).optional(),
	assetIds: z.array(z.string()).optional(),
});

const videoPlanAssetSchema = z.object({
	id: z.string().min(1),
	type: z.enum(['image', 'video', 'chart', 'quote', 'document', 'stat']),
	src: z.string().optional(),
	caption: z.string().optional(),
	credit: z.string().optional(),
});

const videoPlanShotSchema = z.object({
	id: z.string().min(1),
	start: z.number().nonnegative(),
	end: z.number().positive().optional(),
	layout: debateLayoutSchema.optional(),
	focusSpeaker: speakerSchema.optional(),
	captionSource: z.enum(['segment', 'claim', 'turn']).optional(),
	showClaimIds: z.array(z.string()).optional(),
	showEvidenceIds: z.array(z.string()).optional(),
	showAssetIds: z.array(z.string()).optional(),
	note: z.string().optional(),
});

export const videoPlanSchema = z.object({
	cast: z.array(videoPlanCastSchema).optional(),
	chapters: z.array(videoPlanChapterSchema).optional(),
	claims: z.array(videoPlanClaimSchema).optional(),
	evidence: z.array(videoPlanEvidenceSchema).optional(),
	assets: z.array(videoPlanAssetSchema).optional(),
	shots: z.array(videoPlanShotSchema).optional(),
});

export const userDebateSchema = z.object({
	title: z.string(),
	subtitle: z.string(),
	audioFile: z.string(),
	outputName: z.string().optional(),
	layout: debateLayoutSchema.optional(),
	renderDurationInSeconds: z.number().positive().optional(),
	timeline: debateTimelineSchema,
	videoPlan: videoPlanSchema.optional(),
});

type SpeakerTheme = {
	label: string;
	subtitle: string;
	accent: string;
	surface: string;
	glow: string;
	line: string;
};

type DebateTurn = z.infer<typeof debateTurnSchema>;
type DebateSegment = z.infer<typeof debateSegmentSchema>;
type VideoPlan = z.infer<typeof videoPlanSchema>;
type VideoPlanCast = z.infer<typeof videoPlanCastSchema>;
type VideoPlanClaim = z.infer<typeof videoPlanClaimSchema>;
type VideoPlanEvidence = z.infer<typeof videoPlanEvidenceSchema>;
type VideoPlanAsset = z.infer<typeof videoPlanAssetSchema>;
type VideoPlanShot = z.infer<typeof videoPlanShotSchema>;

export type DebateTimeline = z.infer<typeof debateTimelineSchema>;
export type UserDebateProps = z.infer<typeof userDebateSchema>;
export type UserDebateLayout = z.infer<typeof debateLayoutSchema>;

type PreparedSpeaker = {
	id: string;
	side: z.infer<typeof speakerSideSchema>;
	role: 'host' | 'debater' | 'moderator' | 'guest';
	displayName: string;
	avatarLabel: string;
	avatarImage?: string;
	theme: SpeakerTheme;
};

type ResolvedChapter = {
	id: string;
	label: string;
	start: number;
	end: number;
};

type ResolvedClaim = {
	id: string;
	speaker: string;
	side: z.infer<typeof speakerSideSchema>;
	turn?: number;
	start: number;
	end: number;
	summary: string;
	type: 'claim' | 'rebuttal' | 'question' | 'moderation' | 'closing';
	topic: string;
	evidenceIds: string[];
	targets: string[];
};

type ResolvedEvidence = {
	id: string;
	claimId?: string;
	start: number;
	end: number;
	label: string;
	summary: string;
	kind: 'support' | 'example' | 'data' | 'context' | 'flagged';
	assetIds: string[];
};

type ResolvedVideoPlan = {
	cast: PreparedSpeaker[];
	chapters: ResolvedChapter[];
	claims: ResolvedClaim[];
	evidence: ResolvedEvidence[];
	assets: VideoPlanAsset[];
	shots: Array<
		VideoPlanShot & {
			end: number;
		}
	>;
};

type PreparedSceneData = {
	title: string;
	subtitle: string;
	audioFile: string;
	layout: UserDebateLayout;
	renderDuration: number;
	processedTurns: DebateTurn[];
	processedSegments: Array<
		DebateSegment & {
			accepted: boolean;
		}
	>;
	speakerCatalog: PreparedSpeaker[];
	currentTime: number;
	turn: DebateTurn;
	segment: DebateSegment & {accepted: boolean};
	nextSegment: (DebateSegment & {accepted: boolean}) | null;
	turnProgress: number;
	segmentProgress: number;
	totalProgress: number;
	activeSpeaker: PreparedSpeaker;
	activeTheme: SpeakerTheme;
	activeTurnNumber: string;
	captionEntrance: number;
	captionFontSize: number;
	resolvedPlan: ResolvedVideoPlan;
	currentChapter: ResolvedChapter | null;
	currentClaim: ResolvedClaim | null;
	currentEvidence: ResolvedEvidence[];
	activeShot: (ResolvedVideoPlan['shots'][number] & {end: number}) | null;
};

const knownSpeakerThemes: Record<string, SpeakerTheme> = {
	host: {
		label: '主持',
		subtitle: 'Host',
		accent: '#F5D06F',
		surface: '#47381A',
		glow: 'rgba(245, 208, 111, 0.3)',
		line: 'rgba(245, 208, 111, 0.92)',
	},
	positive: {
		label: '正方',
		subtitle: 'Affirmative',
		accent: '#26E0C8',
		surface: '#103A3E',
		glow: 'rgba(38, 224, 200, 0.34)',
		line: 'rgba(38, 224, 200, 0.9)',
	},
	negative: {
		label: '反方',
		subtitle: 'Negative',
		accent: '#FF8B5E',
		surface: '#40231A',
		glow: 'rgba(255, 139, 94, 0.3)',
		line: 'rgba(255, 139, 94, 0.92)',
	},
};

const fallbackSpeakerThemes: SpeakerTheme[] = [
	{
		label: 'Speaker',
		subtitle: 'Speaker',
		accent: '#6CC8FF',
		surface: '#152B40',
		glow: 'rgba(108, 200, 255, 0.28)',
		line: 'rgba(108, 200, 255, 0.88)',
	},
	{
		label: 'Speaker',
		subtitle: 'Speaker',
		accent: '#F17FF8',
		surface: '#3D1F44',
		glow: 'rgba(241, 127, 248, 0.28)',
		line: 'rgba(241, 127, 248, 0.9)',
	},
	{
		label: 'Speaker',
		subtitle: 'Speaker',
		accent: '#95E85A',
		surface: '#223B1A',
		glow: 'rgba(149, 232, 90, 0.28)',
		line: 'rgba(149, 232, 90, 0.9)',
	},
];

const uiSubtitleLines = {
	dual: 'Dual debate layout',
	podcast: 'Podcast waveform layout',
	mindmap: 'Argument map layout',
};

const cleanTranscriptText = (text: string) => {
	return text
		.replace(/\[[^\]]+\]/g, ' ')
		.replace(/\s*\n+\s*/g, ' ')
		.replace(/\s{2,}/g, ' ')
		.replace(/\s+([，。！？；：、,.!?;:])/g, '$1')
		.replace(/([（(])\s+/g, '$1')
		.replace(/\s+([）)])/g, '$1')
		.trim();
};

const clamp = (value: number, min: number, max: number) => {
	return Math.min(max, Math.max(min, value));
};

const formatTime = (seconds: number) => {
	const totalSeconds = Math.max(0, Math.floor(seconds));
	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const remainingSeconds = totalSeconds % 60;

	return [hours, minutes, remainingSeconds]
		.map((part) => String(part).padStart(2, '0'))
		.join(':');
};

const truncateText = (text: string, maxLength: number) => {
	if (text.length <= maxLength) {
		return text;
	}

	return `${text.slice(0, maxLength).trim()}…`;
};

const splitSentences = (text: string) => {
	return cleanTranscriptText(text)
		.split(/(?<=[。！？!?；;])/u)
		.map((sentence) => sentence.trim())
		.filter(Boolean);
};

const summarizeText = (text: string, maxLength = 82) => {
	const cleaned = cleanTranscriptText(text);
	const firstSentence = splitSentences(cleaned)[0] ?? cleaned;
	return truncateText(firstSentence || cleaned, maxLength);
};

const hashSpeaker = (speaker: string) => {
	let hash = 0;

	for (const character of speaker) {
		hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
	}

	return hash;
};

const speakerTitleCase = (speaker: string) => {
	return speaker
		.replace(/[_-]+/g, ' ')
		.trim()
		.replace(/\b\w/g, (match) => match.toUpperCase());
};

const withAlpha = (hexColor: string, alpha: number) => {
	const shortHex = /^#([\da-fA-F]{3})$/;
	const longHex = /^#([\da-fA-F]{6})$/;

	const normalize = (value: string) => {
		if (shortHex.test(value)) {
			return value
				.slice(1)
				.split('')
				.map((part) => `${part}${part}`)
				.join('');
		}

		if (longHex.test(value)) {
			return value.slice(1);
		}

		return null;
	};

	const normalized = normalize(hexColor.trim());
	if (!normalized) {
		return hexColor;
	}

	const red = Number.parseInt(normalized.slice(0, 2), 16);
	const green = Number.parseInt(normalized.slice(2, 4), 16);
	const blue = Number.parseInt(normalized.slice(4, 6), 16);
	return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
};

const getSpeakerTheme = (speaker: string, accentOverride?: string): SpeakerTheme => {
	const normalized = speaker.trim().toLowerCase();
	const known = knownSpeakerThemes[normalized];
	const fallback =
		fallbackSpeakerThemes[hashSpeaker(normalized) % fallbackSpeakerThemes.length];
	const baseTheme = known
		? known
		: {
				...fallback,
				label: speakerTitleCase(speaker),
				subtitle: normalized.toUpperCase().slice(0, 18) || 'SPEAKER',
			};

	if (!accentOverride) {
		return baseTheme;
	}

	return {
		...baseTheme,
		accent: accentOverride,
		surface: withAlpha(accentOverride, 0.18),
		glow: withAlpha(accentOverride, 0.32),
		line: withAlpha(accentOverride, 0.92),
	};
};

const findCurrentItem = <T extends {start: number; end: number}>(
	items: T[],
	time: number,
) => {
	let fallback = items[0] as T;

	for (const item of items) {
		if (time < item.start) {
			return fallback;
		}

		if (time >= item.start && time < item.end) {
			return item;
		}

		fallback = item;
	}

	return items[items.length - 1] as T;
};

const findNextItem = <T extends {start: number}>(items: T[], time: number) => {
	for (const item of items) {
		if (item.start > time) {
			return item;
		}
	}

	return null;
};

const findLatestStartedItem = <T extends {start: number}>(items: T[], time: number) => {
	let latest: T | null = null;

	for (const item of items) {
		if (item.start > time) {
			break;
		}

		latest = item;
	}

	return latest;
};

const findLatestSpeakerSegment = <
	T extends {
		speaker: string;
		start: number;
	},
>(
	items: T[],
	speaker: string,
	time: number,
) => {
	let latest: T | null = null;

	for (const item of items) {
		if (item.start > time) {
			break;
		}

		if (item.speaker === speaker) {
			latest = item;
		}
	}

	return latest;
};

const getCaptionFontSize = (textLength: number) => {
	if (textLength > 150) {
		return 42;
	}

	if (textLength > 110) {
		return 50;
	}

	if (textLength > 75) {
		return 58;
	}

	return 68;
};

const normalizeTurns = (turns: DebateTurn[]) => {
	return [...turns]
		.map((turn, index) => ({
			...turn,
			turn: Number.isFinite(turn.turn) ? turn.turn : index + 1,
			duration:
				typeof turn.duration === 'number' && turn.duration > 0
					? turn.duration
					: Math.max(0.001, turn.end - turn.start),
			content: cleanTranscriptText(turn.content),
		}))
		.filter((turn) => turn.end > turn.start)
		.sort((a, b) => a.start - b.start);
};

const normalizeSegments = (segments: DebateSegment[], turns: DebateTurn[]) => {
	const normalizedSegments = [...segments]
		.map((segment) => ({
			...segment,
			text: cleanTranscriptText(segment.text),
			accepted: segment.accepted ?? true,
		}))
		.filter((segment) => segment.end > segment.start && segment.text.length > 0)
		.sort((a, b) => a.start - b.start);

	if (normalizedSegments.length > 0) {
		return normalizedSegments;
	}

	return turns.map((turn) => ({
		turn: turn.turn,
		speaker: turn.speaker,
		text: turn.content,
		start: turn.start,
		end: turn.end,
		accepted: true,
	}));
};

const defaultSpeakerSide = (
	speaker: string,
	fallbackIndex: number,
): z.infer<typeof speakerSideSchema> => {
	const normalized = speaker.trim().toLowerCase();

	if (normalized === 'host' || normalized === 'moderator') {
		return 'center';
	}

	if (normalized === 'positive' || normalized === 'affirmative' || normalized === 'pro') {
		return 'left';
	}

	if (
		normalized === 'negative' ||
		normalized === 'opposition' ||
		normalized === 'con'
	) {
		return 'right';
	}

	return fallbackIndex % 2 === 0 ? 'left' : 'right';
};

const buildSpeakerCatalog = (
	speakerIds: string[],
	videoPlan: VideoPlan | undefined,
): PreparedSpeaker[] => {
	const castById = new Map(
		(videoPlan?.cast ?? []).map((castMember) => [castMember.id, castMember]),
	);
	let alternatingIndex = 0;

	return speakerIds.map((speakerId) => {
		const castMember = castById.get(speakerId);
		const side =
			castMember?.side ?? defaultSpeakerSide(speakerId, alternatingIndex++);
		const role =
			castMember?.role ??
			(side === 'center' ? 'host' : 'debater');
		const theme = getSpeakerTheme(speakerId, castMember?.accent);
		const displayName = castMember?.displayName ?? theme.label;
		const avatarLabel =
			castMember?.avatarLabel ?? displayName.slice(0, /[\u4e00-\u9fff]/u.test(displayName) ? 2 : 1);

		return {
			id: speakerId,
			side,
			role,
			displayName,
			avatarLabel,
			avatarImage: castMember?.avatarImage,
			theme,
		};
	});
};

const defaultChapterLabel = (index: number, total: number) => {
	if (total === 1) {
		return '辩论全程';
	}

	if (index === 0) {
		return '开场立论';
	}

	if (index === total - 1) {
		return '总结陈词';
	}

	return `攻防阶段 ${index}`;
};

const buildFallbackChapters = (
	turns: DebateTurn[],
	renderDuration: number,
): ResolvedChapter[] => {
	if (turns.length === 0) {
		return [
			{
				id: 'chapter-1',
				label: '辩论全程',
				start: 0,
				end: renderDuration,
			},
		];
	}

	const chunkSize = turns.length > 18 ? 4 : 3;
	const groups: DebateTurn[][] = [];

	for (let index = 0; index < turns.length; index += chunkSize) {
		groups.push(turns.slice(index, index + chunkSize));
	}

	return groups.map((group, index) => ({
		id: `chapter-${index + 1}`,
		label: defaultChapterLabel(index, groups.length),
		start: group[0].start,
		end: Math.min(renderDuration, group[group.length - 1].end),
	}));
};

const buildFallbackClaimsAndEvidence = (
	turns: DebateTurn[],
	segments: Array<DebateSegment & {accepted: boolean}>,
	title: string,
	speakerCatalog: PreparedSpeaker[],
) => {
	const speakerById = new Map(speakerCatalog.map((speaker) => [speaker.id, speaker]));
	const fallbackClaims: ResolvedClaim[] = [];
	const fallbackEvidence: ResolvedEvidence[] = [];
	const lastClaimBySide: Record<z.infer<typeof speakerSideSchema>, string | null> = {
		left: null,
		right: null,
		center: null,
	};

	for (const turn of turns) {
		const speaker = speakerById.get(turn.speaker);
		const side = speaker?.side ?? 'center';
		const evidenceIds: string[] = [];
		const turnSegments = segments
			.filter((segment) => segment.turn === turn.turn)
			.slice(0, 2);

		turnSegments.forEach((segment, index) => {
			const evidenceId = `evidence-${turn.turn}-${index + 1}`;
			evidenceIds.push(evidenceId);
			fallbackEvidence.push({
				id: evidenceId,
				claimId: `claim-turn-${turn.turn}`,
				start: segment.start,
				end: segment.end,
				label: `${speaker?.displayName ?? turn.speaker} · ${index + 1}`,
				summary: summarizeText(segment.text, 74),
				kind: segment.accepted ? 'support' : 'flagged',
				assetIds: [],
			});
		});

		const oppositeSide =
			side === 'left' ? 'right' : side === 'right' ? 'left' : 'center';
		const opposingClaim = lastClaimBySide[oppositeSide];
		const claimType =
			side === 'center'
				? 'moderation'
				: turn.turn >= turns.length - 1
					? 'closing'
					: opposingClaim
						? 'rebuttal'
						: 'claim';

		fallbackClaims.push({
			id: `claim-turn-${turn.turn}`,
			speaker: turn.speaker,
			side,
			turn: turn.turn,
			start: turn.start,
			end: turn.end,
			summary: summarizeText(turn.content, 92),
			type: claimType,
			topic: title,
			evidenceIds,
			targets: opposingClaim ? [opposingClaim] : [],
		});

		lastClaimBySide[side] = `claim-turn-${turn.turn}`;
	}

	return {
		fallbackClaims,
		fallbackEvidence,
	};
};

const resolvePlan = ({
	videoPlan,
	title,
	renderDuration,
	turns,
	segments,
	speakerCatalog,
}: {
	videoPlan: VideoPlan | undefined;
	title: string;
	renderDuration: number;
	turns: DebateTurn[];
	segments: Array<DebateSegment & {accepted: boolean}>;
	speakerCatalog: PreparedSpeaker[];
}): ResolvedVideoPlan => {
	const speakerById = new Map(speakerCatalog.map((speaker) => [speaker.id, speaker]));
	const turnByNumber = new Map(turns.map((turn) => [turn.turn, turn]));
	const {fallbackClaims, fallbackEvidence} = buildFallbackClaimsAndEvidence(
		turns,
		segments,
		title,
		speakerCatalog,
	);
	const chaptersInput =
		videoPlan?.chapters && videoPlan.chapters.length > 0
			? videoPlan.chapters
			: buildFallbackChapters(turns, renderDuration);
	const claimsInput =
		videoPlan?.claims && videoPlan.claims.length > 0
			? videoPlan.claims
			: fallbackClaims;
	const evidenceInput =
		videoPlan?.evidence && videoPlan.evidence.length > 0
			? videoPlan.evidence
			: fallbackEvidence;

	const chapters = chaptersInput
		.map((chapter, index) => {
			const nextChapterStart = chaptersInput[index + 1]?.start ?? renderDuration;
			const end =
				typeof chapter.end === 'number'
					? chapter.end
					: nextChapterStart;
			return {
				id: chapter.id,
				label: chapter.label,
				start: chapter.start,
				end: Math.max(chapter.start + 0.001, Math.min(renderDuration, end)),
			};
		})
		.filter((chapter) => chapter.end > chapter.start)
		.sort((a, b) => a.start - b.start);

	const claims = claimsInput
		.map((claim, index) => {
			const relatedTurn = typeof claim.turn === 'number' ? turnByNumber.get(claim.turn) : null;
			const speaker = speakerById.get(claim.speaker);
			const nextClaimStart = claimsInput[index + 1]?.start ?? renderDuration;
			const inferredEnd =
				typeof claim.end === 'number'
					? claim.end
					: relatedTurn?.end ?? nextClaimStart;

			return {
				id: claim.id,
				speaker: claim.speaker,
				side: speaker?.side ?? defaultSpeakerSide(claim.speaker, index),
				turn: claim.turn,
				start: claim.start,
				end: Math.max(claim.start + 0.001, Math.min(renderDuration, inferredEnd)),
				summary: summarizeText(claim.summary, 92),
				type: claim.type ?? 'claim',
				topic: claim.topic ?? title,
				evidenceIds: claim.evidenceIds ?? [],
				targets: claim.targets ?? [],
			};
		})
		.filter((claim) => claim.end > claim.start)
		.sort((a, b) => a.start - b.start);

	const evidence = evidenceInput
		.map((item, index) => {
			const nextEvidenceStart = evidenceInput[index + 1]?.start ?? renderDuration;
			const inferredEnd =
				typeof item.end === 'number' ? item.end : nextEvidenceStart;
			return {
				id: item.id,
				claimId: item.claimId,
				start: item.start,
				end: Math.max(item.start + 0.001, Math.min(renderDuration, inferredEnd)),
				label: item.label,
				summary: summarizeText(item.summary, 74),
				kind: item.kind ?? 'support',
				assetIds: item.assetIds ?? [],
			};
		})
		.filter((item) => item.end > item.start)
		.sort((a, b) => a.start - b.start);

	const shots = (videoPlan?.shots ?? [])
		.map((shot, index, array) => {
			const nextShotStart = array[index + 1]?.start ?? renderDuration;
			return {
				...shot,
				end:
					typeof shot.end === 'number'
						? Math.max(shot.start + 0.001, Math.min(renderDuration, shot.end))
						: Math.max(shot.start + 0.001, nextShotStart),
			};
		})
		.filter((shot) => shot.end > shot.start)
		.sort((a, b) => a.start - b.start);

	return {
		cast: speakerCatalog,
		chapters,
		claims,
		evidence,
		assets: videoPlan?.assets ?? [],
		shots,
	};
};

const getEvidenceTone = (kind: ResolvedEvidence['kind']) => {
	switch (kind) {
		case 'flagged':
			return {
				border: 'rgba(255, 165, 122, 0.68)',
				background: 'rgba(255, 107, 53, 0.12)',
				label: 'QA flagged',
			};
		case 'data':
			return {
				border: 'rgba(108, 200, 255, 0.82)',
				background: 'rgba(108, 200, 255, 0.12)',
				label: 'Data',
			};
		case 'context':
			return {
				border: 'rgba(245, 208, 111, 0.8)',
				background: 'rgba(245, 208, 111, 0.12)',
				label: 'Context',
			};
		case 'example':
			return {
				border: 'rgba(149, 232, 90, 0.82)',
				background: 'rgba(149, 232, 90, 0.12)',
				label: 'Example',
			};
		default:
			return {
				border: 'rgba(38, 224, 200, 0.8)',
				background: 'rgba(38, 224, 200, 0.12)',
				label: 'Support',
			};
	}
};

const SpeakerAvatar: React.FC<{
	speaker: PreparedSpeaker;
	active: boolean;
	size: number;
}> = ({speaker, active, size}) => {
	const frame = useCurrentFrame();
	const pulse = interpolate(Math.sin(frame / 12), [-1, 1], [0.985, 1.025]);

	return (
		<div
			style={{
				width: size,
				height: size,
				borderRadius: size,
				border: `2px solid ${
					active ? speaker.theme.line : 'rgba(255,255,255,0.14)'
				}`,
				boxShadow: active ? `0 0 34px ${speaker.theme.glow}` : 'none',
				background: speaker.avatarImage
					? `center / cover no-repeat url(${staticFile(speaker.avatarImage)})`
					: `radial-gradient(circle at 35% 28%, ${withAlpha(
							speaker.theme.accent,
							0.78,
					  )} 0%, ${speaker.theme.surface} 68%, rgba(6, 9, 20, 0.88) 100%)`,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				fontSize: size * 0.34,
				fontWeight: 800,
				letterSpacing: 1,
				color: 'white',
				transform: active ? `scale(${pulse})` : 'scale(1)',
			}}
		>
			{speaker.avatarImage ? null : speaker.avatarLabel}
		</div>
	);
};

const HeaderBlock: React.FC<{
	title: string;
	subtitle: string;
	currentTime: number;
	renderDuration: number;
	layout: UserDebateLayout;
	currentChapter: ResolvedChapter | null;
}> = ({title, subtitle, currentTime, renderDuration, layout, currentChapter}) => {
	return (
		<div
			style={{
				display: 'flex',
				justifyContent: 'space-between',
				alignItems: 'flex-start',
				gap: 32,
			}}
		>
			<div style={{display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 1280}}>
				<div
					style={{
						fontSize: 20,
						letterSpacing: 4,
						textTransform: 'uppercase',
						opacity: 0.58,
					}}
				>
					{uiSubtitleLines[layout]}
				</div>
				<div
					style={{
						fontSize: 72,
						lineHeight: 1.02,
						fontWeight: 800,
					}}
				>
					{title}
				</div>
				<div
					style={{
						fontSize: 24,
						opacity: 0.72,
					}}
				>
					{subtitle}
				</div>
			</div>
			<div
				style={{
					display: 'flex',
					flexDirection: 'column',
					alignItems: 'flex-end',
					gap: 12,
					padding: '18px 22px',
					borderRadius: 24,
					backgroundColor: 'rgba(255,255,255,0.05)',
					border: '1px solid rgba(255,255,255,0.08)',
					minWidth: 270,
				}}
			>
				<div
					style={{
						fontSize: 42,
						fontWeight: 700,
						fontVariantNumeric: 'tabular-nums',
					}}
				>
					{formatTime(currentTime)}
				</div>
				<div
					style={{
						fontSize: 22,
						opacity: 0.74,
						fontVariantNumeric: 'tabular-nums',
					}}
				>
					{formatTime(renderDuration)} total
				</div>
				<div
					style={{
						fontSize: 16,
						opacity: 0.7,
						padding: '6px 12px',
						borderRadius: 9999,
						backgroundColor: 'rgba(255,255,255,0.06)',
						textTransform: 'uppercase',
						letterSpacing: 1.5,
					}}
				>
					{currentChapter ? currentChapter.label : 'Live debate'}
				</div>
			</div>
		</div>
	);
};

const GlassPill: React.FC<{
	label: string;
	accent?: string;
}> = ({label, accent = 'rgba(255,255,255,0.14)'}) => {
	return (
		<div
			style={{
				padding: '10px 14px',
				borderRadius: 9999,
				backgroundColor: withAlpha(accent, 0.14),
				border: `1px solid ${withAlpha(accent, 0.42)}`,
				fontSize: 15,
				fontWeight: 700,
				letterSpacing: 1.2,
				textTransform: 'uppercase',
				color: accent.startsWith('#') ? accent : 'white',
				whiteSpace: 'nowrap',
			}}
		>
			{label}
		</div>
	);
};

const LayoutAtmosphere: React.FC<{
	data: PreparedSceneData;
}> = ({data}) => {
	const leftAccent =
		data.speakerCatalog.find((speaker) => speaker.side === 'left')?.theme.accent ??
		'#26E0C8';
	const rightAccent =
		data.speakerCatalog.find((speaker) => speaker.side === 'right')?.theme.accent ??
		'#FF8B5E';

	if (data.layout === 'podcast') {
		return (
			<AbsoluteFill style={{pointerEvents: 'none'}}>
				<AbsoluteFill
					style={{
						background:
							'radial-gradient(circle at 50% 44%, rgba(255,255,255,0.05), transparent 24%), linear-gradient(180deg, rgba(10,14,29,0.0) 0%, rgba(4,7,16,0.6) 100%)',
					}}
				/>
				<AbsoluteFill
					style={{
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							width: 820,
							height: 820,
							borderRadius: 820,
							border: `1px solid ${withAlpha(data.activeTheme.accent, 0.14)}`,
							boxShadow: `0 0 120px ${withAlpha(data.activeTheme.accent, 0.14)}`,
						}}
					/>
				</AbsoluteFill>
				<AbsoluteFill
					style={{
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							width: 560,
							height: 560,
							borderRadius: 560,
							border: `1px solid ${withAlpha(leftAccent, 0.14)}`,
						}}
					/>
				</AbsoluteFill>
				<AbsoluteFill
					style={{
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							width: 340,
							height: 340,
							borderRadius: 340,
							border: `1px solid ${withAlpha(rightAccent, 0.18)}`,
						}}
					/>
				</AbsoluteFill>
			</AbsoluteFill>
		);
	}

	if (data.layout === 'mindmap') {
		return (
			<AbsoluteFill style={{pointerEvents: 'none'}}>
				<AbsoluteFill
					style={{
						backgroundImage:
							'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
						backgroundSize: '80px 80px',
						opacity: 0.22,
					}}
				/>
				<AbsoluteFill
					style={{
						background:
							`radial-gradient(circle at 24% 52%, ${withAlpha(leftAccent, 0.16)}, transparent 24%), radial-gradient(circle at 76% 52%, ${withAlpha(rightAccent, 0.16)}, transparent 24%), radial-gradient(circle at 50% 28%, ${withAlpha(data.activeTheme.accent, 0.12)}, transparent 22%)`,
					}}
				/>
			</AbsoluteFill>
		);
	}

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<AbsoluteFill
				style={{
					background: `linear-gradient(90deg, ${withAlpha(
						leftAccent,
						0.08,
					)} 0%, transparent 24%, transparent 76%, ${withAlpha(rightAccent, 0.08)} 100%)`,
				}}
			/>
			<AbsoluteFill
				style={{
					display: 'flex',
					justifyContent: 'center',
				}}
			>
				<div
					style={{
						width: 1,
						height: '100%',
						background: `linear-gradient(180deg, transparent 0%, ${withAlpha(
							data.activeTheme.accent,
							0.24,
						)} 18%, ${withAlpha(data.activeTheme.accent, 0.08)} 82%, transparent 100%)`,
					}}
				/>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const TimelineStrip: React.FC<{
	processedTurns: DebateTurn[];
	currentTime: number;
	totalProgress: number;
}> = ({processedTurns, currentTime, totalProgress}) => {
	return (
		<div
			style={{
				display: 'flex',
				flexDirection: 'column',
				gap: 18,
			}}
		>
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					gap: 18,
				}}
			>
				<div
					style={{
						fontSize: 18,
						opacity: 0.58,
						textTransform: 'uppercase',
						letterSpacing: 3,
					}}
				>
					Turn flow
				</div>
				<div
					style={{
						flex: 1,
						height: 10,
						borderRadius: 9999,
						backgroundColor: 'rgba(255,255,255,0.08)',
						overflow: 'hidden',
					}}
				>
					<div
						style={{
							height: '100%',
							width: `${totalProgress * 100}%`,
							borderRadius: 9999,
							background:
								'linear-gradient(90deg, #F5D06F 0%, #26E0C8 48%, #FF8B5E 100%)',
						}}
					/>
				</div>
			</div>
			<div
				style={{
					display: 'flex',
					gap: 10,
					alignItems: 'stretch',
				}}
			>
				{processedTurns.map((item) => {
					const theme = getSpeakerTheme(item.speaker);
					const isActive = currentTime >= item.start && currentTime < item.end;

					return (
						<div
							key={`${item.turn}-${item.speaker}-${item.start}`}
							style={{
								flex: item.duration ?? Math.max(0.001, item.end - item.start),
								padding: '12px 14px',
								borderRadius: 18,
								backgroundColor: isActive
									? theme.surface
									: 'rgba(255,255,255,0.04)',
								border: `1px solid ${
									isActive ? theme.line : 'rgba(255,255,255,0.05)'
								}`,
								display: 'flex',
								flexDirection: 'column',
								gap: 6,
								boxShadow: isActive ? `0 0 24px ${theme.glow}` : 'none',
							}}
						>
							<div
								style={{
									fontSize: 14,
									letterSpacing: 2,
									textTransform: 'uppercase',
									opacity: 0.62,
								}}
							>
								{theme.label}
							</div>
							<div
								style={{
									fontSize: 20,
									fontWeight: 700,
									fontVariantNumeric: 'tabular-nums',
								}}
							>
								#{item.turn}
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
};

const CaptionCard: React.FC<{
	segment: DebateSegment & {accepted: boolean};
	segmentProgress: number;
	activeTheme: SpeakerTheme;
	captionEntrance: number;
	captionFontSize: number;
	speakerLabel: string;
	turnNumber: number;
	totalTurns: number;
	compact?: boolean;
}> = ({
	segment,
	segmentProgress,
	activeTheme,
	captionEntrance,
	captionFontSize,
	speakerLabel,
	turnNumber,
	totalTurns,
	compact = false,
}) => {
	return (
		<div
			style={{
				width: '100%',
				padding: compact ? '28px 34px 24px 34px' : '36px 42px 30px 42px',
				borderRadius: compact ? 30 : 38,
				backgroundColor: compact
					? 'rgba(8, 14, 28, 0.88)'
					: 'rgba(9, 15, 30, 0.84)',
				border: `1px solid ${activeTheme.line}`,
				boxShadow: `0 18px 60px rgba(0, 0, 0, 0.34), 0 0 54px ${activeTheme.glow}`,
				transform: `scale(${0.978 + captionEntrance * 0.022})`,
				opacity: 0.78 + captionEntrance * 0.22,
				display: 'flex',
				flexDirection: 'column',
				gap: 20,
			}}
		>
			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'center',
					gap: 24,
				}}
			>
				<div
					style={{
						fontSize: compact ? 20 : 22,
						textTransform: 'uppercase',
						letterSpacing: 3,
						color: activeTheme.accent,
					}}
				>
					{speakerLabel} · 回合 {turnNumber}/{totalTurns}
				</div>
				<div
					style={{
						fontSize: compact ? 18 : 20,
						opacity: 0.64,
						fontVariantNumeric: 'tabular-nums',
					}}
				>
					{formatTime(segment.start)} - {formatTime(segment.end)}
				</div>
			</div>
			<div
				style={{
					fontSize: compact ? Math.max(30, captionFontSize - 12) : captionFontSize,
					lineHeight: 1.16,
					fontWeight: 700,
					letterSpacing: 0.4,
					whiteSpace: 'pre-wrap',
					overflowWrap: 'anywhere',
				}}
			>
				{segment.text}
			</div>
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					gap: 18,
				}}
			>
				<div
					style={{
						flex: 1,
						height: 8,
						borderRadius: 9999,
						backgroundColor: 'rgba(255,255,255,0.08)',
						overflow: 'hidden',
					}}
				>
					<div
						style={{
							height: '100%',
							width: `${segmentProgress * 100}%`,
							borderRadius: 9999,
							backgroundColor: activeTheme.accent,
						}}
					/>
				</div>
				<div
					style={{
						fontSize: compact ? 18 : 20,
						opacity: 0.72,
						minWidth: compact ? 160 : 190,
						textAlign: 'right',
						fontVariantNumeric: 'tabular-nums',
						color: segment.accepted ? 'white' : '#FFD0BF',
					}}
				>
					{segment.accepted ? 'QA accepted' : 'QA flagged'}
				</div>
			</div>
		</div>
	);
};

const DebateSidePanel: React.FC<{
	speaker: PreparedSpeaker;
	isActive: boolean;
	progress: number;
	segment: (DebateSegment & {accepted: boolean}) | null;
}> = ({speaker, isActive, progress, segment}) => {
	const frame = useCurrentFrame();
	const idleScale = interpolate(Math.sin(frame / 18), [-1, 1], [0.996, 1.012]);

	return (
		<div
			style={{
				flex: 1,
				minWidth: 0,
				display: 'flex',
				flexDirection: 'column',
				gap: 20,
				padding: 28,
				borderRadius: 30,
				backgroundColor: isActive
					? speaker.theme.surface
					: 'rgba(255,255,255,0.045)',
				border: `1px solid ${
					isActive ? speaker.theme.line : 'rgba(255,255,255,0.08)'
				}`,
				boxShadow: isActive ? `0 0 34px ${speaker.theme.glow}` : 'none',
				transform: isActive ? `scale(${idleScale})` : 'scale(1)',
			}}
		>
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'space-between',
					gap: 16,
				}}
			>
				<div style={{display: 'flex', alignItems: 'center', gap: 18}}>
					<SpeakerAvatar active={isActive} size={92} speaker={speaker} />
					<div style={{display: 'flex', flexDirection: 'column', gap: 6}}>
						<div
							style={{
								fontSize: 34,
								fontWeight: 800,
								letterSpacing: 1,
							}}
						>
							{speaker.displayName}
						</div>
						<div
							style={{
								fontSize: 16,
								textTransform: 'uppercase',
								letterSpacing: 2,
								opacity: 0.72,
							}}
						>
							{isActive ? 'Speaking now' : 'Latest position'}
						</div>
					</div>
				</div>
				<div
					style={{
						padding: '8px 14px',
						borderRadius: 9999,
						backgroundColor: withAlpha(speaker.theme.accent, isActive ? 0.2 : 0.1),
						color: speaker.theme.accent,
						fontSize: 16,
						fontWeight: 700,
						letterSpacing: 1,
					}}
				>
					{speaker.side.toUpperCase()}
				</div>
			</div>
			<div
				style={{
					fontSize: 36,
					lineHeight: 1.18,
					fontWeight: 700,
					minHeight: 170,
					opacity: segment ? 1 : 0.58,
				}}
			>
				{segment ? summarizeText(segment.text, 120) : 'Waiting for this side to speak.'}
			</div>
			<div
				style={{
					display: 'flex',
					flexDirection: 'column',
					gap: 10,
					marginTop: 'auto',
				}}
			>
				<div
					style={{
						height: 8,
						borderRadius: 9999,
						backgroundColor: 'rgba(255,255,255,0.08)',
						overflow: 'hidden',
					}}
				>
					<div
						style={{
							height: '100%',
							width: `${progress * 100}%`,
							borderRadius: 9999,
							backgroundColor: speaker.theme.accent,
						}}
					/>
				</div>
				<div
					style={{
						fontSize: 17,
						opacity: 0.68,
					}}
				>
					{segment
						? `${formatTime(segment.start)} - ${formatTime(segment.end)}`
						: 'No segment yet'}
				</div>
			</div>
		</div>
	);
};

const PodcastWaveform: React.FC<{
	accent: string;
	secondaryAccent: string;
	energy: number;
	speakerBias: number;
}> = ({accent, secondaryAccent, energy, speakerBias}) => {
	const frame = useCurrentFrame();
	const waveform = Array.from({length: 56}, (_, index) => {
		const rhythm =
			Math.sin(frame / 3.4 + index * 0.58 + speakerBias) * 0.34 +
			Math.cos(frame / 5.6 + index * 0.33 + speakerBias * 0.5) * 0.24;
		const pulse = Math.sin(frame / 2.2 + index * 0.9) * 0.18;
		return clamp(Math.abs(rhythm + pulse) * (0.38 + energy * 0.72), 0.04, 1);
	});

	return (
		<div
			style={{
				height: 220,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				gap: 8,
				padding: '0 18px',
			}}
		>
			{waveform.map((sample, index) => {
				const height = 26 + sample * 170;
				const glow = index % 2 === 0 ? accent : secondaryAccent;

				return (
					<div
						key={`wave-${index}`}
						style={{
							width: 10,
							height,
							borderRadius: 9999,
							background: `linear-gradient(180deg, ${withAlpha(
								glow,
								0.18,
							)} 0%, ${glow} 100%)`,
							boxShadow: `0 0 20px ${withAlpha(glow, 0.28)}`,
						}}
					/>
				);
			})}
		</div>
	);
};

const MindmapClaimCard: React.FC<{
	claim: ResolvedClaim;
	speaker: PreparedSpeaker | null;
	active: boolean;
}> = ({claim, speaker, active}) => {
	const theme = speaker?.theme ?? getSpeakerTheme(claim.speaker);
	return (
		<div
			style={{
				padding: '18px 20px',
				borderRadius: 24,
				backgroundColor: active ? theme.surface : 'rgba(255,255,255,0.045)',
				border: `1px solid ${
					active ? theme.line : 'rgba(255,255,255,0.08)'
				}`,
				boxShadow: active ? `0 0 26px ${theme.glow}` : 'none',
				display: 'flex',
				flexDirection: 'column',
				gap: 10,
			}}
		>
			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'center',
					gap: 12,
				}}
			>
				<div
					style={{
						fontSize: 18,
						textTransform: 'uppercase',
						letterSpacing: 2,
						color: theme.accent,
					}}
				>
					{speaker?.displayName ?? speakerTitleCase(claim.speaker)}
				</div>
				<div
					style={{
						fontSize: 14,
						opacity: 0.62,
					}}
				>
					{claim.type}
				</div>
			</div>
			<div
				style={{
					fontSize: 28,
					lineHeight: 1.16,
					fontWeight: 700,
				}}
			>
				{claim.summary}
			</div>
			<div
				style={{
					fontSize: 15,
					opacity: 0.6,
				}}
			>
				{formatTime(claim.start)} - {formatTime(claim.end)}
			</div>
		</div>
	);
};

const DualLayout: React.FC<{
	data: PreparedSceneData;
}> = ({data}) => {
	const leftSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'left') ?? null;
	const rightSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'right') ?? null;
	const hostSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'center') ?? null;
	const hostSegment =
		hostSpeaker !== null
			? findLatestSpeakerSegment(
					data.processedSegments,
					hostSpeaker.id,
					data.currentTime,
			  )
			: null;
	const leftSegment =
		leftSpeaker !== null
			? data.turn.speaker === leftSpeaker.id
				? data.segment
				: findLatestSpeakerSegment(
						data.processedSegments,
						leftSpeaker.id,
						data.currentTime,
				  )
			: null;
	const rightSegment =
		rightSpeaker !== null
			? data.turn.speaker === rightSpeaker.id
				? data.segment
				: findLatestSpeakerSegment(
						data.processedSegments,
						rightSpeaker.id,
						data.currentTime,
				  )
			: null;
	const centerBanner =
		data.activeSpeaker.side === 'center'
			? summarizeText(data.segment.text, 140)
			: data.currentClaim?.summary ?? summarizeText(data.segment.text, 140);

	return (
		<AbsoluteFill
			style={{
				padding: '52px 68px 40px 68px',
				display: 'flex',
				flexDirection: 'column',
				gap: 24,
			}}
		>
			<HeaderBlock
				currentChapter={data.currentChapter}
				currentTime={data.currentTime}
				layout={data.layout}
				renderDuration={data.renderDuration}
				subtitle={data.subtitle}
				title={data.title}
			/>

			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'center',
					gap: 14,
					flexWrap: 'wrap',
				}}
			>
				<div
					style={{
						display: 'flex',
						gap: 12,
						alignItems: 'center',
						flexWrap: 'wrap',
					}}
				>
					{leftSpeaker ? (
						<GlassPill
							accent={leftSpeaker.theme.accent}
							label={`${leftSpeaker.displayName} channel`}
						/>
					) : null}
					<GlassPill accent={data.activeTheme.accent} label={`Round ${data.turn.turn}`} />
					{rightSpeaker ? (
						<GlassPill
							accent={rightSpeaker.theme.accent}
							label={`${rightSpeaker.displayName} channel`}
						/>
					) : null}
				</div>
				<GlassPill
					accent={data.activeTheme.accent}
					label={data.currentChapter?.label ?? 'Live exchange'}
				/>
			</div>

			{hostSpeaker ? (
				<div
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: 18,
						padding: '18px 22px',
						borderRadius: 24,
						backgroundColor:
							data.activeSpeaker.id === hostSpeaker.id
								? hostSpeaker.theme.surface
								: 'rgba(255,255,255,0.04)',
						border: `1px solid ${
							data.activeSpeaker.id === hostSpeaker.id
								? hostSpeaker.theme.line
								: 'rgba(255,255,255,0.08)'
						}`,
						boxShadow:
							data.activeSpeaker.id === hostSpeaker.id
								? `0 0 24px ${hostSpeaker.theme.glow}`
								: 'none',
					}}
				>
					<SpeakerAvatar
						active={data.activeSpeaker.id === hostSpeaker.id}
						size={64}
						speaker={hostSpeaker}
					/>
					<div
						style={{
							display: 'flex',
							flexDirection: 'column',
							gap: 6,
							minWidth: 0,
						}}
					>
						<div
							style={{
								fontSize: 18,
								color: hostSpeaker.theme.accent,
								textTransform: 'uppercase',
								letterSpacing: 2,
							}}
						>
							主持串场
						</div>
						<div
							style={{
								fontSize: 26,
								lineHeight: 1.18,
								fontWeight: 700,
								opacity: hostSegment ? 1 : 0.56,
							}}
						>
							{hostSegment ? summarizeText(hostSegment.text, 170) : 'No host segment yet.'}
						</div>
					</div>
				</div>
			) : null}

			<div
				style={{
					display: 'grid',
					gridTemplateColumns: '1fr 280px 1fr',
					gap: 22,
					alignItems: 'stretch',
				}}
			>
				{leftSpeaker ? (
					<DebateSidePanel
						isActive={data.activeSpeaker.id === leftSpeaker.id}
						progress={data.activeSpeaker.id === leftSpeaker.id ? data.turnProgress : 0}
						segment={leftSegment}
						speaker={leftSpeaker}
					/>
				) : (
					<div />
				)}
				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						justifyContent: 'center',
						alignItems: 'center',
						gap: 20,
						padding: '28px 20px',
						borderRadius: 30,
						background:
							`linear-gradient(180deg, ${withAlpha(leftSpeaker?.theme.accent ?? data.activeTheme.accent, 0.12)} 0%, rgba(255,255,255,0.04) 50%, ${withAlpha(rightSpeaker?.theme.accent ?? data.activeTheme.accent, 0.12)} 100%)`,
						border: `1px solid ${withAlpha(data.activeTheme.accent, 0.24)}`,
						boxShadow: `0 0 34px ${withAlpha(data.activeTheme.accent, 0.1)}`,
					}}
				>
					<div
						style={{
							fontSize: 15,
							textTransform: 'uppercase',
							letterSpacing: 3,
							opacity: 0.58,
						}}
					>
						Debate arena
					</div>
					<div
						style={{
							fontSize: 92,
							fontWeight: 800,
							letterSpacing: 4,
							color: data.activeTheme.accent,
							opacity: 0.9,
						}}
					>
						VS
					</div>
					<div
						style={{
							fontSize: 18,
							textTransform: 'uppercase',
							letterSpacing: 2,
							opacity: 0.64,
						}}
					>
						Turn {data.turn.turn}
					</div>
					<div
						style={{
							fontSize: 16,
							textTransform: 'uppercase',
							letterSpacing: 2,
							opacity: 0.62,
						}}
					>
						Turn {data.turn.turn} of {data.processedTurns.length}
					</div>
					<div
						style={{
							fontSize: 26,
							lineHeight: 1.2,
							fontWeight: 700,
							textAlign: 'center',
						}}
					>
						{centerBanner}
					</div>
				</div>
				{rightSpeaker ? (
					<DebateSidePanel
						isActive={data.activeSpeaker.id === rightSpeaker.id}
						progress={data.activeSpeaker.id === rightSpeaker.id ? data.turnProgress : 0}
						segment={rightSegment}
						speaker={rightSpeaker}
					/>
				) : (
					<div />
				)}
			</div>

			<div style={{display: 'flex', flexDirection: 'column', gap: 20, marginTop: 'auto'}}>
				<CaptionCard
					activeTheme={data.activeTheme}
					captionEntrance={data.captionEntrance}
					captionFontSize={data.captionFontSize}
					segment={data.segment}
					segmentProgress={data.segmentProgress}
					speakerLabel={data.activeSpeaker.displayName}
					totalTurns={data.processedTurns.length}
					turnNumber={data.turn.turn}
				/>
				<TimelineStrip
					currentTime={data.currentTime}
					processedTurns={data.processedTurns}
					totalProgress={data.totalProgress}
				/>
			</div>
		</AbsoluteFill>
	);
};

const PodcastLayout: React.FC<{
	data: PreparedSceneData;
}> = ({data}) => {
	const leftSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'left') ??
		data.speakerCatalog[0] ??
		null;
	const rightSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'right') ??
		data.speakerCatalog[1] ??
		null;
	const hostSpeaker =
		data.speakerCatalog.find((speaker) => speaker.side === 'center') ?? null;
	const leftPanelAccent = leftSpeaker?.theme.accent ?? data.activeTheme.accent;
	const rightPanelAccent = rightSpeaker?.theme.accent ?? data.activeTheme.accent;

	return (
		<AbsoluteFill
			style={{
				padding: '56px 72px 40px 72px',
				display: 'flex',
				flexDirection: 'column',
				gap: 24,
			}}
		>
			<HeaderBlock
				currentChapter={data.currentChapter}
				currentTime={data.currentTime}
				layout={data.layout}
				renderDuration={data.renderDuration}
				subtitle={data.subtitle}
				title={data.title}
			/>

			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'space-between',
					gap: 18,
					flexWrap: 'wrap',
				}}
			>
				<div style={{display: 'flex', gap: 12, flexWrap: 'wrap'}}>
					<GlassPill accent={data.activeTheme.accent} label="On air" />
					<GlassPill
						accent={data.activeTheme.accent}
						label={`Now speaking ${data.activeSpeaker.displayName}`}
					/>
					<GlassPill
						accent={data.activeTheme.accent}
						label={data.currentChapter?.label ?? 'Studio feed'}
					/>
				</div>
				{hostSpeaker ? (
					<div
						style={{
							display: 'flex',
							alignItems: 'center',
							gap: 12,
							padding: '10px 16px',
							borderRadius: 9999,
							backgroundColor: 'rgba(255,255,255,0.05)',
							border: '1px solid rgba(255,255,255,0.08)',
						}}
					>
						<SpeakerAvatar
							active={data.activeSpeaker.id === hostSpeaker.id}
							size={42}
							speaker={hostSpeaker}
						/>
						<div
							style={{
								fontSize: 16,
								opacity: 0.78,
							}}
						>
							Host: {hostSpeaker.displayName}
						</div>
					</div>
				) : null}
			</div>

			<div
				style={{
					flex: 1,
					display: 'grid',
					gridTemplateColumns: '300px 1fr 300px',
					gap: 28,
					alignItems: 'center',
				}}
			>
				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						alignItems: 'center',
						gap: 18,
						padding: '18px 12px',
						borderRadius: 28,
						backgroundColor:
							data.activeSpeaker.id === leftSpeaker?.id
								? withAlpha(leftPanelAccent, 0.1)
								: 'rgba(255,255,255,0.03)',
						border: `1px solid ${
							data.activeSpeaker.id === leftSpeaker?.id
								? withAlpha(leftPanelAccent, 0.32)
								: 'rgba(255,255,255,0.08)'
						}`,
					}}
				>
					{leftSpeaker ? (
						<>
							<SpeakerAvatar
								active={data.activeSpeaker.id === leftSpeaker.id}
								size={220}
								speaker={leftSpeaker}
							/>
							<div
								style={{
									fontSize: 34,
									fontWeight: 800,
								}}
							>
								{leftSpeaker.displayName}
							</div>
							<div
								style={{
									width: '100%',
									height: 8,
									borderRadius: 9999,
									backgroundColor: 'rgba(255,255,255,0.08)',
									overflow: 'hidden',
								}}
							>
								<div
									style={{
										height: '100%',
										width: `${
											data.activeSpeaker.id === leftSpeaker.id
												? data.turnProgress * 100
												: 28
										}%`,
										borderRadius: 9999,
										backgroundColor: leftSpeaker.theme.accent,
									}}
								/>
							</div>
							<div
								style={{
									fontSize: 20,
									lineHeight: 1.2,
									textAlign: 'center',
									opacity: 0.72,
								}}
							>
								{summarizeText(
									findLatestSpeakerSegment(
										data.processedSegments,
										leftSpeaker.id,
										data.currentTime,
									)?.text ?? '',
									90,
								) || 'Waiting for left channel'}
							</div>
						</>
					) : null}
				</div>

				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						gap: 22,
						padding: '30px 24px 16px 24px',
						borderRadius: 42,
						background:
							`radial-gradient(circle at 50% 34%, ${withAlpha(
								data.activeTheme.accent,
								0.12,
							)} 0%, rgba(255,255,255,0.04) 56%, rgba(255,255,255,0.03) 100%)`,
						border: `1px solid ${withAlpha(data.activeTheme.accent, 0.22)}`,
						boxShadow: `0 0 44px ${withAlpha(data.activeTheme.accent, 0.1)}`,
					}}
				>
					<div
						style={{
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center',
							gap: 16,
						}}
					>
						<div
							style={{
								fontSize: 28,
								fontWeight: 700,
								color: data.activeTheme.accent,
								letterSpacing: 1,
							}}
						>
							Live waveform
						</div>
						<GlassPill accent={data.activeTheme.accent} label={`Turn ${data.turn.turn}`} />
					</div>
					<PodcastWaveform
						accent={leftSpeaker?.theme.accent ?? data.activeTheme.accent}
						energy={0.2 + data.segmentProgress * 0.5 + data.turnProgress * 0.3}
						secondaryAccent={rightPanelAccent}
						speakerBias={(data.turn.turn % 7) * 0.42}
					/>
					<div
						style={{
							display: 'flex',
						justifyContent: 'center',
						gap: 10,
						flexWrap: 'wrap',
					}}
					>
						<GlassPill accent={leftPanelAccent} label="channel A" />
						<GlassPill accent={data.activeTheme.accent} label="studio mix" />
						<GlassPill accent={rightPanelAccent} label="channel B" />
					</div>
					<div
						style={{
							display: 'flex',
							justifyContent: 'space-between',
							gap: 18,
						}}
					>
						<div
							style={{
								flex: 1,
								padding: '16px 18px',
								borderRadius: 22,
								backgroundColor: 'rgba(255,255,255,0.04)',
							}}
						>
							<div
								style={{
									fontSize: 16,
									textTransform: 'uppercase',
									letterSpacing: 2,
									opacity: 0.58,
								}}
							>
								Current angle
							</div>
							<div
								style={{
									fontSize: 28,
									fontWeight: 700,
									lineHeight: 1.18,
									marginTop: 8,
								}}
							>
								{data.currentClaim?.summary ?? summarizeText(data.segment.text, 92)}
							</div>
						</div>
						<div
							style={{
								width: 220,
								padding: '16px 18px',
								borderRadius: 22,
								backgroundColor: 'rgba(255,255,255,0.04)',
							}}
						>
							<div
								style={{
									fontSize: 16,
									textTransform: 'uppercase',
									letterSpacing: 2,
									opacity: 0.58,
								}}
							>
								Next segment
							</div>
							<div
								style={{
									fontSize: 20,
									lineHeight: 1.2,
									fontWeight: 700,
									marginTop: 10,
								}}
							>
								{data.nextSegment
									? truncateText(data.nextSegment.text, 70)
									: 'Final segment reached'}
							</div>
						</div>
					</div>
				</div>

				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						alignItems: 'center',
						gap: 18,
						padding: '18px 12px',
						borderRadius: 28,
						backgroundColor:
							data.activeSpeaker.id === rightSpeaker?.id
								? withAlpha(rightPanelAccent, 0.1)
								: 'rgba(255,255,255,0.03)',
						border: `1px solid ${
							data.activeSpeaker.id === rightSpeaker?.id
								? withAlpha(rightPanelAccent, 0.32)
								: 'rgba(255,255,255,0.08)'
						}`,
					}}
				>
					{rightSpeaker ? (
						<>
							<SpeakerAvatar
								active={data.activeSpeaker.id === rightSpeaker.id}
								size={220}
								speaker={rightSpeaker}
							/>
							<div
								style={{
									fontSize: 34,
									fontWeight: 800,
								}}
							>
								{rightSpeaker.displayName}
							</div>
							<div
								style={{
									width: '100%',
									height: 8,
									borderRadius: 9999,
									backgroundColor: 'rgba(255,255,255,0.08)',
									overflow: 'hidden',
								}}
							>
								<div
									style={{
										height: '100%',
										width: `${
											data.activeSpeaker.id === rightSpeaker.id
												? data.turnProgress * 100
												: 28
										}%`,
										borderRadius: 9999,
										backgroundColor: rightSpeaker.theme.accent,
									}}
								/>
							</div>
							<div
								style={{
									fontSize: 20,
									lineHeight: 1.2,
									textAlign: 'center',
									opacity: 0.72,
								}}
							>
								{summarizeText(
									findLatestSpeakerSegment(
										data.processedSegments,
										rightSpeaker.id,
										data.currentTime,
									)?.text ?? '',
									90,
								) || 'Waiting for right channel'}
							</div>
						</>
					) : null}
				</div>
			</div>

			<div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
				<CaptionCard
					activeTheme={data.activeTheme}
					captionEntrance={data.captionEntrance}
					captionFontSize={Math.max(40, data.captionFontSize - 10)}
					compact
					segment={data.segment}
					segmentProgress={data.segmentProgress}
					speakerLabel={data.activeSpeaker.displayName}
					totalTurns={data.processedTurns.length}
					turnNumber={data.turn.turn}
				/>
				<TimelineStrip
					currentTime={data.currentTime}
					processedTurns={data.processedTurns}
					totalProgress={data.totalProgress}
				/>
			</div>
		</AbsoluteFill>
	);
};

const MindmapLayout: React.FC<{
	data: PreparedSceneData;
}> = ({data}) => {
	const speakerById = new Map(
		data.speakerCatalog.map((speaker) => [speaker.id, speaker]),
	);
	const leftAccent =
		data.speakerCatalog.find((speaker) => speaker.side === 'left')?.theme.accent ??
		data.activeTheme.accent;
	const rightAccent =
		data.speakerCatalog.find((speaker) => speaker.side === 'right')?.theme.accent ??
		data.activeTheme.accent;
	const sideClaims = data.resolvedPlan.claims.filter((claim) => claim.side !== 'center');
	const latestLeftClaims = sideClaims
		.filter((claim) => claim.side === 'left' && claim.start <= data.currentTime)
		.slice(-3);
	const latestRightClaims = sideClaims
		.filter((claim) => claim.side === 'right' && claim.start <= data.currentTime)
		.slice(-3);
	const focusClaim =
		data.currentClaim && data.currentClaim.side !== 'center'
			? data.currentClaim
			: findLatestStartedItem(sideClaims, data.currentTime);
	const focusSpeaker = focusClaim ? speakerById.get(focusClaim.speaker) ?? null : null;
	const claimEvidence =
		focusClaim === null
			? data.currentEvidence
			: data.resolvedPlan.evidence
					.filter(
						(evidence) =>
							evidence.claimId === focusClaim.id ||
							focusClaim.evidenceIds.includes(evidence.id),
					)
					.slice(0, 3);

	return (
		<AbsoluteFill
			style={{
				padding: '48px 60px 34px 60px',
				display: 'flex',
				flexDirection: 'column',
				gap: 20,
			}}
		>
			<HeaderBlock
				currentChapter={data.currentChapter}
				currentTime={data.currentTime}
				layout={data.layout}
				renderDuration={data.renderDuration}
				subtitle={data.subtitle}
				title={data.title}
			/>

			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'center',
					gap: 12,
					flexWrap: 'wrap',
				}}
			>
				<div style={{display: 'flex', gap: 12, flexWrap: 'wrap'}}>
					<GlassPill accent={data.activeTheme.accent} label="Argument map" />
					<GlassPill
						accent={data.activeTheme.accent}
						label={`${data.resolvedPlan.claims.length} mapped claims`}
					/>
					<GlassPill
						accent={data.activeTheme.accent}
						label={`${data.resolvedPlan.evidence.length} evidence nodes`}
					/>
				</div>
				<GlassPill
					accent={data.activeTheme.accent}
					label={data.currentChapter?.label ?? 'Timeline-derived map'}
				/>
			</div>

			<div
				style={{
					display: 'grid',
					gridTemplateColumns: '1fr 1fr',
					gap: 18,
				}}
			>
				{(['left', 'right'] as const).map((side) => {
					const claims = side === 'left' ? latestLeftClaims : latestRightClaims;
					const speaker =
						side === 'left'
							? data.speakerCatalog.find((item) => item.side === 'left')
							: data.speakerCatalog.find((item) => item.side === 'right');
					const dominantClaim = claims[claims.length - 1] ?? null;
					const theme = speaker?.theme ?? data.activeTheme;

					return (
						<div
							key={side}
							style={{
								padding: '20px 24px',
								borderRadius: 28,
								backgroundColor: withAlpha(theme.accent, 0.1),
								border: `1px solid ${withAlpha(theme.accent, 0.36)}`,
								display: 'flex',
								flexDirection: 'column',
								gap: 10,
							}}
						>
							<div
								style={{
									display: 'flex',
									justifyContent: 'space-between',
									alignItems: 'center',
								}}
							>
								<div
									style={{
										fontSize: 20,
										textTransform: 'uppercase',
										letterSpacing: 2,
										color: theme.accent,
									}}
								>
									{speaker?.displayName ?? side}
								</div>
								<div
									style={{
										fontSize: 14,
										opacity: 0.62,
									}}
								>
									{claims.length} mapped points
								</div>
							</div>
							<div
								style={{
									fontSize: 28,
									fontWeight: 700,
									lineHeight: 1.16,
									minHeight: 64,
								}}
							>
								{dominantClaim?.summary ?? 'Waiting for mapped arguments.'}
							</div>
						</div>
					);
				})}
			</div>

			<div
				style={{
					flex: 1,
					display: 'grid',
					gridTemplateColumns: '1fr 420px 1fr',
					gap: 18,
					alignItems: 'stretch',
				}}
			>
				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						gap: 16,
					}}
				>
					{latestLeftClaims.length > 0 ? (
						latestLeftClaims.map((claim) => (
							<MindmapClaimCard
								key={claim.id}
								active={focusClaim?.id === claim.id}
								claim={claim}
								speaker={speakerById.get(claim.speaker) ?? null}
							/>
						))
					) : (
						<div
							style={{
								flex: 1,
								padding: '20px',
								borderRadius: 28,
								backgroundColor: 'rgba(255,255,255,0.04)',
								border: '1px solid rgba(255,255,255,0.08)',
								fontSize: 22,
								opacity: 0.6,
							}}
						>
							No left-side claims have started yet.
						</div>
					)}
				</div>

				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						gap: 16,
						padding: '24px 22px',
						borderRadius: 32,
						backgroundColor: 'rgba(255,255,255,0.04)',
						border: `1px solid ${
							focusSpeaker ? focusSpeaker.theme.line : 'rgba(255,255,255,0.08)'
						}`,
						boxShadow: focusSpeaker
							? `0 0 32px ${focusSpeaker.theme.glow}`
							: 'none',
						position: 'relative',
						overflow: 'hidden',
					}}
				>
					<div
						style={{
							position: 'absolute',
							left: -40,
							top: '50%',
							width: 120,
							height: 1,
							background: `linear-gradient(90deg, transparent 0%, ${withAlpha(
								leftAccent ?? data.activeTheme.accent,
								0.36,
							)} 100%)`,
						}}
					/>
					<div
						style={{
							position: 'absolute',
							right: -40,
							top: '50%',
							width: 120,
							height: 1,
							background: `linear-gradient(90deg, ${withAlpha(
								rightAccent ?? data.activeTheme.accent,
								0.36,
							)} 0%, transparent 100%)`,
						}}
					/>
					<div
						style={{
							fontSize: 18,
							textTransform: 'uppercase',
							letterSpacing: 3,
							opacity: 0.62,
						}}
					>
						Topic node
					</div>
					<div
						style={{
							padding: '22px 20px',
							borderRadius: 28,
							backgroundColor: 'rgba(8, 14, 28, 0.88)',
							border: '1px solid rgba(255,255,255,0.08)',
							textAlign: 'center',
						}}
					>
						<div
							style={{
								fontSize: 20,
								opacity: 0.62,
								textTransform: 'uppercase',
								letterSpacing: 2,
							}}
						>
							Debate topic
						</div>
						<div
							style={{
								fontSize: 42,
								lineHeight: 1.08,
								fontWeight: 800,
								marginTop: 10,
							}}
						>
							{focusClaim?.topic ?? data.title}
						</div>
						<div
							style={{
								display: 'flex',
								justifyContent: 'center',
								gap: 10,
								flexWrap: 'wrap',
								marginTop: 16,
							}}
						>
							<GlassPill
								accent={focusSpeaker?.theme.accent ?? data.activeTheme.accent}
								label={focusSpeaker?.displayName ?? 'Timeline'}
							/>
							{focusClaim ? (
								<GlassPill
									accent={focusSpeaker?.theme.accent ?? data.activeTheme.accent}
									label={focusClaim.type}
								/>
							) : null}
						</div>
					</div>
					<div
						style={{
							padding: '18px 20px',
							borderRadius: 24,
							backgroundColor: focusSpeaker
								? withAlpha(focusSpeaker.theme.accent, 0.12)
								: 'rgba(255,255,255,0.04)',
						}}
					>
						<div
							style={{
								fontSize: 16,
								textTransform: 'uppercase',
								letterSpacing: 2,
								opacity: 0.62,
							}}
						>
							Current mapped point
						</div>
						<div
							style={{
								fontSize: 30,
								lineHeight: 1.16,
								fontWeight: 700,
								marginTop: 10,
							}}
						>
							{focusClaim?.summary ?? summarizeText(data.segment.text, 92)}
						</div>
						<div
							style={{
								fontSize: 16,
								opacity: 0.6,
								marginTop: 12,
							}}
						>
							{focusSpeaker
								? `${focusSpeaker.displayName} · ${formatTime(
										focusClaim?.start ?? data.segment.start,
								  )} - ${formatTime(focusClaim?.end ?? data.segment.end)}`
								: 'Timeline-derived fallback point'}
						</div>
					</div>
					<div
						style={{
							display: 'flex',
							flexDirection: 'column',
							gap: 12,
						}}
					>
						<div
							style={{
								fontSize: 16,
								textTransform: 'uppercase',
								letterSpacing: 2,
								opacity: 0.62,
							}}
						>
							Evidence ribbon
						</div>
						{claimEvidence.length > 0 ? (
							claimEvidence.map((item) => {
								const tone = getEvidenceTone(item.kind);
								return (
									<div
										key={item.id}
										style={{
											padding: '14px 16px',
											borderRadius: 20,
											backgroundColor: tone.background,
											border: `1px solid ${tone.border}`,
											display: 'flex',
											flexDirection: 'column',
											gap: 6,
										}}
									>
										<div
											style={{
												display: 'flex',
												justifyContent: 'space-between',
												alignItems: 'center',
												gap: 12,
											}}
										>
											<div
												style={{
													fontSize: 15,
													textTransform: 'uppercase',
													letterSpacing: 2,
													opacity: 0.72,
												}}
											>
												{tone.label}
											</div>
											<div
												style={{
													fontSize: 14,
													opacity: 0.6,
												}}
											>
												{formatTime(item.start)}
											</div>
										</div>
										<div
											style={{
												fontSize: 20,
												lineHeight: 1.16,
												fontWeight: 700,
											}}
										>
											{item.summary}
										</div>
									</div>
								);
							})
						) : (
							<div
								style={{
									padding: '16px',
									borderRadius: 20,
									backgroundColor: 'rgba(255,255,255,0.04)',
									fontSize: 18,
									opacity: 0.58,
								}}
							>
								Add `evidence[]` entries in `video-plan.json` to make this richer.
							</div>
						)}
					</div>
				</div>

				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						gap: 16,
					}}
				>
					{latestRightClaims.length > 0 ? (
						latestRightClaims.map((claim) => (
							<MindmapClaimCard
								key={claim.id}
								active={focusClaim?.id === claim.id}
								claim={claim}
								speaker={speakerById.get(claim.speaker) ?? null}
							/>
						))
					) : (
						<div
							style={{
								flex: 1,
								padding: '20px',
								borderRadius: 28,
								backgroundColor: 'rgba(255,255,255,0.04)',
								border: '1px solid rgba(255,255,255,0.08)',
								fontSize: 22,
								opacity: 0.6,
							}}
						>
							No right-side claims have started yet.
						</div>
					)}
				</div>
			</div>

			<div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
				<CaptionCard
					activeTheme={data.activeTheme}
					captionEntrance={data.captionEntrance}
					captionFontSize={Math.max(34, data.captionFontSize - 14)}
					compact
					segment={data.segment}
					segmentProgress={data.segmentProgress}
					speakerLabel={data.activeSpeaker.displayName}
					totalTurns={data.processedTurns.length}
					turnNumber={data.turn.turn}
				/>
				<div
					style={{
						display: 'flex',
						justifyContent: 'space-between',
						gap: 16,
					}}
				>
					<div
						style={{
							flex: 1,
							padding: '14px 18px',
							borderRadius: 20,
							backgroundColor: 'rgba(255,255,255,0.04)',
							fontSize: 20,
						}}
					>
						{data.nextSegment
							? `Next: ${truncateText(data.nextSegment.text, 110)}`
							: 'Final segment reached'}
					</div>
					<div
						style={{
							width: 320,
							padding: '14px 18px',
							borderRadius: 20,
							backgroundColor: data.activeShot
								? 'rgba(255,255,255,0.07)'
								: 'rgba(255,255,255,0.04)',
							fontSize: 18,
							opacity: 0.78,
						}}
					>
						{data.activeShot
							? `Shot note: ${data.activeShot.note ?? 'Active plan shot'}`
							: 'No explicit shot plan loaded'}
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

export const DebateVideo: React.FC<UserDebateProps> = ({
	audioFile,
	layout,
	renderDurationInSeconds,
	subtitle,
	timeline,
	title,
	videoPlan,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const normalizedLayout = layout ?? 'dual';
	const processedTurns = normalizeTurns(timeline.turns);
	const processedSegments = normalizeSegments(timeline.segments, processedTurns);
	const renderDuration = Math.min(
		renderDurationInSeconds ?? timeline.duration,
		timeline.duration,
	);
	const speakerIds = [
		...new Set([
			...processedTurns.map((turn) => turn.speaker),
			...processedSegments.map((segment) => segment.speaker),
			...(videoPlan?.cast ?? []).map((castMember) => castMember.id),
		]),
	];
	const speakerCatalog = buildSpeakerCatalog(speakerIds, videoPlan);
	const currentTime = frame / fps;
	const turn = findCurrentItem(processedTurns, currentTime);
	const segment = findCurrentItem(processedSegments, currentTime);
	const nextSegment = findNextItem(processedSegments, currentTime);
	const turnProgress = clamp(
		(currentTime - turn.start) /
			Math.max(0.001, turn.duration ?? turn.end - turn.start),
		0,
		1,
	);
	const segmentProgress = clamp(
		(currentTime - segment.start) / Math.max(0.001, segment.end - segment.start),
		0,
		1,
	);
	const totalProgress = clamp(currentTime / renderDuration, 0, 1);
	const activeSpeaker =
		speakerCatalog.find((speaker) => speaker.id === turn.speaker) ?? speakerCatalog[0];
	const activeTheme = activeSpeaker?.theme ?? getSpeakerTheme(turn.speaker);
	const captionFrame = Math.max(0, frame - Math.floor(segment.start * fps));
	const captionEntrance = spring({
		fps,
		frame: captionFrame,
		config: {
			damping: 200,
			mass: 0.8,
			stiffness: 120,
		},
	});
	const captionFontSize = getCaptionFontSize(segment.text.length);
	const activeTurnNumber = String(turn.turn).padStart(2, '0');
	const resolvedPlan = resolvePlan({
		videoPlan,
		title,
		renderDuration,
		turns: processedTurns,
		segments: processedSegments,
		speakerCatalog,
	});
	const currentChapter =
		resolvedPlan.chapters.length > 0
			? findCurrentItem(resolvedPlan.chapters, currentTime)
			: null;
	const currentClaim =
		resolvedPlan.claims.length > 0
			? findLatestStartedItem(resolvedPlan.claims, currentTime)
			: null;
	const currentEvidence =
		currentClaim === null
			? []
			: resolvedPlan.evidence.filter(
					(evidence) =>
						evidence.claimId === currentClaim.id ||
						currentClaim.evidenceIds.includes(evidence.id),
			  );
	const activeShot =
		resolvedPlan.shots.length > 0
			? findLatestStartedItem(resolvedPlan.shots, currentTime)
			: null;
	const preparedData: PreparedSceneData = {
		title,
		subtitle,
		audioFile,
		layout: normalizedLayout,
		renderDuration,
		processedTurns,
		processedSegments,
		speakerCatalog,
		currentTime,
		turn,
		segment,
		nextSegment,
		turnProgress,
		segmentProgress,
		totalProgress,
		activeSpeaker,
		activeTheme,
		activeTurnNumber,
		captionEntrance,
		captionFontSize,
		resolvedPlan,
		currentChapter,
		currentClaim,
		currentEvidence,
		activeShot,
	};

	return (
		<AbsoluteFill
			style={{
				backgroundColor: '#060914',
				color: 'white',
				fontFamily:
					'"Aptos", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif',
			}}
		>
			<Html5Audio src={staticFile(audioFile)} />
			<AbsoluteFill
				style={{
					background:
						'radial-gradient(circle at 18% 18%, rgba(38, 224, 200, 0.22), transparent 30%), radial-gradient(circle at 80% 24%, rgba(255, 139, 94, 0.18), transparent 28%), linear-gradient(180deg, #081122 0%, #050814 100%)',
				}}
			/>
			<AbsoluteFill
				style={{
					opacity: 0.78,
					transform: `translate(${Math.sin(frame / 120) * 42}px, ${
						Math.cos(frame / 160) * 30
					}px)`,
					background:
						'radial-gradient(circle at 26% 30%, rgba(38, 224, 200, 0.14), transparent 26%), radial-gradient(circle at 70% 68%, rgba(255, 139, 94, 0.12), transparent 24%)',
				}}
			/>
			<LayoutAtmosphere data={preparedData} />
			{normalizedLayout === 'podcast' ? <PodcastLayout data={preparedData} /> : null}
			{normalizedLayout === 'mindmap' ? <MindmapLayout data={preparedData} /> : null}
			{normalizedLayout === 'dual' ? <DualLayout data={preparedData} /> : null}
		</AbsoluteFill>
	);
};
