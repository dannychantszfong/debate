const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {bundle} = require('@remotion/bundler');
const {renderMedia, selectComposition} = require('@remotion/renderer');

const compositionId = 'user-debate-video';
const entryPoint = path.resolve(__dirname, 'src/UserDebate/entry.tsx');
const publicInputDir = path.resolve(__dirname, 'public/user-debate/input');
const defaultOutputDir = path.resolve(__dirname, '../../../output/video');
const PROGRESS_BAR_WIDTH = 28;
const validLayouts = ['dual', 'podcast', 'mindmap'];
const validOpenGlRenderers = [
	'swangle',
	'angle',
	'egl',
	'swiftshader',
	'vulkan',
	'angle-egl',
];

const usage = `
Usage:
  node render-user-debate.cjs --json "<path-to-transcript.json>" [--audio "<path-to-audio.wav>"] [--plan "<path-to-video-plan.json>"] [--layout dual|podcast|mindmap] [--out "<path-to-output.mp4>"] [--title "<title>"] [--subtitle "<subtitle>"] [--max-seconds 60] [--concurrency 75%] [--gl angle] [--port 8090] [--keep-bundle] [--keep-staged-audio]

Examples:
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json"
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --out "..\\..\\..\\output\\video\\debate.mp4"
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --layout podcast
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --layout mindmap --plan "..\\..\\..\\output\\audio\\example.video-plan.json"
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --max-seconds 90
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --concurrency 75%
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --gl angle
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --port 8090
  node render-user-debate.cjs --json "..\\..\\..\\output\\audio\\example.json" --keep-bundle --keep-staged-audio
`.trim();

const knownSpeakerLabels = {
	host: '主持',
	positive: '正方',
	negative: '反方',
};

const supportsDynamicTerminal =
	Boolean(process.stdout.isTTY) &&
	typeof process.stdout.clearLine === 'function' &&
	typeof process.stdout.cursorTo === 'function';

let lastDynamicLength = 0;

const clamp = (value, min, max) => {
	return Math.min(max, Math.max(min, value));
};

const formatMilliseconds = (value) => {
	if (!Number.isFinite(value) || value === null || value === undefined || value < 0) {
		return '--';
	}

	const totalSeconds = Math.max(0, Math.round(value / 1000));
	const minutes = Math.floor(totalSeconds / 60);
	const seconds = totalSeconds % 60;

	if (minutes > 0) {
		return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
	}

	return `${seconds}s`;
};

const padRight = (value, width) => {
	const text = String(value);
	if (text.length >= width) {
		return text;
	}

	return text + ' '.repeat(width - text.length);
};

const makeProgressBar = (progress) => {
	const safeProgress = clamp(progress ?? 0, 0, 1);
	const filled = Math.round(safeProgress * PROGRESS_BAR_WIDTH);
	return `[${'#'.repeat(filled)}${'-'.repeat(PROGRESS_BAR_WIDTH - filled)}]`;
};

const writeProgressLine = (text, done = false) => {
	if (!supportsDynamicTerminal) {
		console.log(text);
		return;
	}

	const padded = text.padEnd(lastDynamicLength, ' ');
	lastDynamicLength = padded.length;
	process.stdout.clearLine(0);
	process.stdout.cursorTo(0);
	process.stdout.write(padded);

	if (done) {
		process.stdout.write('\n');
		lastDynamicLength = 0;
	}
};

const logPhase = (label, progress, details, done = false) => {
	const percent = `${Math.round(clamp(progress ?? 0, 0, 1) * 100)}%`.padStart(4, ' ');
	const line = `${padRight(label, 12)} ${makeProgressBar(progress)} ${percent} ${details}`.trimEnd();
	writeProgressLine(line, done);
};

const finalizeProgressLine = () => {
	if (!supportsDynamicTerminal || lastDynamicLength === 0) {
		return;
	}

	process.stdout.write('\n');
	lastDynamicLength = 0;
};

const parseArgs = (argv) => {
	const args = {};

	for (let index = 0; index < argv.length; index++) {
		const token = argv[index];

		if (!token.startsWith('--')) {
			continue;
		}

		const key = token.slice(2);
		const next = argv[index + 1];

		if (!next || next.startsWith('--')) {
			args[key] = true;
			continue;
		}

		args[key] = next;
		index++;
	}

	return args;
};

const assertFileExists = (filePath, flagName) => {
	if (!filePath || !fs.existsSync(filePath)) {
		throw new Error(`Missing ${flagName} file: ${filePath}`);
	}
};

const ensureDirectory = (directory) => {
	fs.mkdirSync(directory, {recursive: true});
};

const isInsideDirectory = (targetPath, directory) => {
	if (!targetPath || !directory) {
		return false;
	}

	const relative = path.relative(path.resolve(directory), path.resolve(targetPath));
	return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
};

const removePathIfExists = (targetPath) => {
	if (!targetPath || !fs.existsSync(targetPath)) {
		return false;
	}

	fs.rmSync(targetPath, {recursive: true, force: true});
	return true;
};

const sanitizeFileStem = (value) => {
	const sanitized = value
		.replace(/[<>:"/\\|?*\u0000-\u001F]/g, '-')
		.replace(/\s+/g, ' ')
		.trim();

	return sanitized.length > 0 ? sanitized : 'user-debate-render';
};

const cleanTranscriptText = (text) => {
	return String(text ?? '')
		.replace(/\[[^\]]+\]/g, ' ')
		.replace(/\s*\n+\s*/g, ' ')
		.replace(/\s{2,}/g, ' ')
		.replace(/\s+([，。！？；：、,.!?;:])/g, '$1')
		.trim();
};

const parsePositiveNumber = (value) => {
	if (value === undefined || value === null || value === '') {
		return null;
	}

	const parsed = Number(value);
	return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};

const parseConcurrency = (value) => {
	if (value === undefined || value === null || value === '') {
		return null;
	}

	if (typeof value !== 'string') {
		throw new Error(`Invalid concurrency value: ${String(value)}`);
	}

	const trimmed = value.trim();

	if (trimmed.endsWith('%')) {
		const percent = Number(trimmed.slice(0, -1));
		if (!Number.isFinite(percent) || percent <= 0 || percent > 100) {
			throw new Error(
				`Invalid --concurrency percentage "${value}". Use a number like 12 or a percentage like 75%.`,
			);
		}

		return `${percent}%`;
	}

	const numeric = Number(trimmed);
	if (!Number.isFinite(numeric) || numeric <= 0) {
		throw new Error(
			`Invalid --concurrency value "${value}". Use a number like 12 or a percentage like 75%.`,
		);
	}

	return Math.floor(numeric);
};

const parseGlRenderer = (value) => {
	if (value === undefined || value === null || value === '') {
		return null;
	}

	if (!validOpenGlRenderers.includes(value)) {
		throw new Error(
			`Invalid --gl value "${value}". Accepted values: ${validOpenGlRenderers.join(', ')}`,
		);
	}

	return value;
};

const parsePort = (value) => {
	if (value === undefined || value === null || value === '') {
		return 8090;
	}

	const parsed = Number(value);
	if (!Number.isInteger(parsed) || parsed < 1024 || parsed > 65535) {
		throw new Error(`Invalid --port value "${value}". Use an integer between 1024 and 65535.`);
	}

	return parsed;
};

const parseLayout = (value) => {
	if (value === undefined || value === null || value === '') {
		return 'dual';
	}

	if (!validLayouts.includes(value)) {
		throw new Error(
			`Invalid --layout value "${value}". Accepted values: ${validLayouts.join(', ')}`,
		);
	}

	return value;
};

const isTemporaryBundlePath = (bundlePath) => {
	if (!bundlePath) {
		return false;
	}

	const resolvedBundlePath = path.resolve(bundlePath);
	const resolvedTempDir = path.resolve(os.tmpdir());
	return (
		path.basename(resolvedBundlePath).startsWith('remotion-webpack-bundle-') &&
		path.dirname(resolvedBundlePath) === resolvedTempDir
	);
};

const normalizeTurns = (rawTurns) => {
	return (Array.isArray(rawTurns) ? rawTurns : [])
		.map((turn, index) => {
			const start = Number(turn.start);
			const end = Number(turn.end);
			const duration =
				parsePositiveNumber(turn.duration) ?? Math.max(0.001, end - start);

			return {
				turn: Number.isFinite(Number(turn.turn)) ? Number(turn.turn) : index + 1,
				speaker: String(turn.speaker ?? 'speaker'),
				start,
				end,
				duration,
				content: cleanTranscriptText(turn.content),
			};
		})
		.filter(
			(turn) =>
				Number.isFinite(turn.start) &&
				Number.isFinite(turn.end) &&
				turn.end > turn.start,
		)
		.sort((left, right) => left.start - right.start);
};

const normalizeSegments = (rawSegments, turns) => {
	const segments = (Array.isArray(rawSegments) ? rawSegments : [])
		.map((segment, index) => ({
			turn: Number.isFinite(Number(segment.turn))
				? Number(segment.turn)
				: turns[index]?.turn ?? index + 1,
			speaker: String(segment.speaker ?? turns[index]?.speaker ?? 'speaker'),
			text: cleanTranscriptText(segment.text),
			start: Number(segment.start),
			end: Number(segment.end),
			accepted:
				typeof segment.accepted === 'boolean' ? segment.accepted : true,
		}))
		.filter(
			(segment) =>
				Number.isFinite(segment.start) &&
				Number.isFinite(segment.end) &&
				segment.end > segment.start &&
				segment.text.length > 0,
		)
		.sort((left, right) => left.start - right.start);

	if (segments.length > 0) {
		return segments;
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

const normalizeTimeline = (rawData) => {
	const turns = normalizeTurns(rawData.turns);

	if (turns.length === 0) {
		throw new Error('Transcript JSON did not contain any valid turns.');
	}

	const segments = normalizeSegments(rawData.segments, turns);
	const derivedDuration = Math.max(
		0,
		...turns.map((turn) => turn.end),
		...segments.map((segment) => segment.end),
	);
	const duration = parsePositiveNumber(rawData.duration) ?? derivedDuration;

	if (!duration || duration <= 0) {
		throw new Error('Could not derive a valid debate duration from the transcript JSON.');
	}

	return {
		duration,
		turns,
		segments,
	};
};

const deriveTitleFromStem = (stem) => {
	const parts = stem.split('_').filter(Boolean);
	const chineseCandidates = parts.filter((part) => /[\u4e00-\u9fff]/.test(part));

	if (chineseCandidates.length > 0) {
		return chineseCandidates.sort((left, right) => right.length - left.length)[0];
	}

	return stem
		.replace(/^tts_debate_transcript_/i, '')
		.replace(/_\d{8}_\d{6}$/u, '')
		.replace(/_/g, ' ')
		.trim();
};

const formatDuration = (durationInSeconds) => {
	const totalSeconds = Math.max(0, Math.round(durationInSeconds));
	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const seconds = totalSeconds % 60;

	if (hours > 0) {
		return `${hours}h ${minutes}m ${seconds}s`;
	}

	if (minutes > 0) {
		return `${minutes}m ${seconds}s`;
	}

	return `${seconds}s`;
};

const deriveSubtitle = (timeline) => {
	const speakers = [
		...new Set(timeline.turns.map((turn) => String(turn.speaker ?? 'speaker'))),
	].map((speaker) => {
		const normalized = speaker.toLowerCase();
		return knownSpeakerLabels[normalized] ?? speaker;
	});

	return `${speakers.join(' / ')} · ${timeline.turns.length} turns · ${formatDuration(
		timeline.duration,
	)}`;
};

const tryResolveSiblingAudio = (jsonPath) => {
	const directory = path.dirname(jsonPath);
	const stem = path.basename(jsonPath, path.extname(jsonPath));
	const candidates = ['.wav', '.mp3', '.m4a', '.aac', '.flac'].map((extension) =>
		path.join(directory, `${stem}${extension}`),
	);

	return candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
};

const tryResolveSiblingVideoPlan = (jsonPath) => {
	const directory = path.dirname(jsonPath);
	const stem = path.basename(jsonPath, path.extname(jsonPath));
	const candidates = [
		`${stem}.video-plan.json`,
		`${stem}.plan.json`,
		'video-plan.json',
	].map((candidate) => path.join(directory, candidate));

	return candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
};

const resolveAudioPath = ({audioArg, jsonPath, rawData}) => {
	if (audioArg) {
		const resolved = path.resolve(audioArg);
		assertFileExists(resolved, '--audio');
		return resolved;
	}

	if (rawData.audio) {
		const candidate = path.isAbsolute(rawData.audio)
			? rawData.audio
			: path.resolve(path.dirname(jsonPath), rawData.audio);

		if (fs.existsSync(candidate)) {
			return candidate;
		}
	}

	const siblingAudio = tryResolveSiblingAudio(jsonPath);

	if (siblingAudio) {
		return siblingAudio;
	}

	throw new Error(
		'Could not resolve an audio file. Pass --audio explicitly or ensure the JSON "audio" field points to a real file.',
	);
};

const resolveVideoPlan = ({planArg, jsonPath, rawData}) => {
	if (planArg) {
		const resolved = path.resolve(planArg);
		assertFileExists(resolved, '--plan');
		return {
			videoPlan: JSON.parse(fs.readFileSync(resolved, 'utf8')),
			videoPlanPath: resolved,
			videoPlanSource: 'explicit-plan-file',
		};
	}

	if (rawData.videoPlan && typeof rawData.videoPlan === 'object') {
		return {
			videoPlan: rawData.videoPlan,
			videoPlanPath: null,
			videoPlanSource: 'embedded-json',
		};
	}

	if (rawData.video_plan && typeof rawData.video_plan === 'object') {
		return {
			videoPlan: rawData.video_plan,
			videoPlanPath: null,
			videoPlanSource: 'embedded-json',
		};
	}

	if (typeof rawData.videoPlan === 'string' || typeof rawData.video_plan === 'string') {
		const relativePath = rawData.videoPlan ?? rawData.video_plan;
		const resolved = path.isAbsolute(relativePath)
			? relativePath
			: path.resolve(path.dirname(jsonPath), relativePath);

		if (fs.existsSync(resolved)) {
			return {
				videoPlan: JSON.parse(fs.readFileSync(resolved, 'utf8')),
				videoPlanPath: resolved,
				videoPlanSource: 'json-referenced-plan-file',
			};
		}
	}

	const siblingPlan = tryResolveSiblingVideoPlan(jsonPath);

	if (siblingPlan) {
		return {
			videoPlan: JSON.parse(fs.readFileSync(siblingPlan, 'utf8')),
			videoPlanPath: siblingPlan,
			videoPlanSource: 'sibling-plan-file',
		};
	}

	return {
		videoPlan: null,
		videoPlanPath: null,
		videoPlanSource: 'timeline-fallback',
	};
};

const stageAudioFile = (audioPath, outputStem) => {
	ensureDirectory(publicInputDir);

	const extension = path.extname(audioPath) || '.wav';
	const destinationName = `${sanitizeFileStem(outputStem)}${extension.toLowerCase()}`;
	const destinationPath = path.join(publicInputDir, destinationName);

	if (fs.existsSync(destinationPath)) {
		fs.unlinkSync(destinationPath);
	}

	let stageMethod = 'hard-link';

	try {
		fs.linkSync(audioPath, destinationPath);
	} catch {
		stageMethod = 'copy';
		fs.copyFileSync(audioPath, destinationPath);
	}

	return {
		stageMethod,
		relativeStaticPath: `user-debate/input/${destinationName}`,
		stagedPath: destinationPath,
	};
};

const getOutputLocation = (outArg, outputStem) => {
	if (outArg) {
		return path.resolve(outArg);
	}

	return path.join(defaultOutputDir, `${sanitizeFileStem(outputStem)}.mp4`);
};

const main = async () => {
	const args = parseArgs(process.argv.slice(2));

	if (args.help || args.h || !args.json) {
		console.log(usage);
		return;
	}

	const jsonPath = path.resolve(args.json);
	assertFileExists(jsonPath, '--json');

	const rawData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
	const timeline = normalizeTimeline(rawData);
	const audioPath = resolveAudioPath({
		audioArg: args.audio,
		jsonPath,
		rawData,
	});
	const jsonStem = sanitizeFileStem(path.basename(jsonPath, path.extname(jsonPath)));
	const title = args.title ? String(args.title) : deriveTitleFromStem(jsonStem);
	const subtitle = args.subtitle ? String(args.subtitle) : deriveSubtitle(timeline);
	const maxSeconds = parsePositiveNumber(args['max-seconds']);
	const concurrency = parseConcurrency(args.concurrency);
	const glRenderer = parseGlRenderer(args.gl);
	const port = parsePort(args.port);
	const layout = parseLayout(args.layout);
	const resolvedVideoPlan = resolveVideoPlan({
		planArg: args.plan,
		jsonPath,
		rawData,
	});
	const keepBundle = Boolean(args['keep-bundle'] || args['keep-cache']);
	const keepStagedAudio = Boolean(args['keep-staged-audio']);
	const outputStem = args['output-name']
		? sanitizeFileStem(String(args['output-name']))
		: layout === 'dual'
			? jsonStem
			: `${jsonStem}-${layout}`;
	const outputLocation = getOutputLocation(args.out, outputStem);
	const outputName = sanitizeFileStem(
		path.basename(outputLocation, path.extname(outputLocation)),
	);
	const stagedAudio = stageAudioFile(audioPath, outputName);
	const inputProps = {
		title,
		subtitle,
		audioFile: stagedAudio.relativeStaticPath,
		layout,
		outputName,
		renderDurationInSeconds: maxSeconds ?? undefined,
		timeline,
		videoPlan: resolvedVideoPlan.videoPlan ?? undefined,
	};

	ensureDirectory(path.dirname(outputLocation));
	fs.writeFileSync(
		path.join(
			path.dirname(outputLocation),
			`${path.basename(outputLocation, path.extname(outputLocation))}.input.json`,
		),
		JSON.stringify(
			{
				jsonPath,
				audioPath,
				layout,
				port,
				videoPlanPath: resolvedVideoPlan.videoPlanPath,
				videoPlanSource: resolvedVideoPlan.videoPlanSource,
				stagedAudioPath: stagedAudio.stagedPath,
				stageMethod: stagedAudio.stageMethod,
				stagedAudioRetention: keepStagedAudio ? 'retained' : 'removed-after-render',
				bundleRetention: keepBundle ? 'retained' : 'removed-after-render',
				inputProps,
			},
			null,
			2,
		),
		'utf8',
	);

	let bundled = null;

	try {
		console.log(`Bundling Remotion entry: ${entryPoint}`);
		bundled = await bundle({
			entryPoint,
			webpackOverride: (config) => config,
			onProgressCallback: ({bundling, copying}) => {
				if (copying.doneIn === null && copying.bytes > 0) {
					logPhase(
						'Copy assets',
						1,
						`${Math.round(copying.bytes / 1024 / 1024)} MB`,
					);
					return;
				}

				const bundlingProgress = bundling.progress ?? 0;
				logPhase(
					'Bundling',
					bundlingProgress,
					`${Math.round(bundlingProgress * 100)}%`,
					bundlingProgress >= 0.9999,
				);
			},
		});
		finalizeProgressLine();

		console.log(`Selecting composition "${compositionId}"`);
		const composition = await selectComposition({
			serveUrl: bundled,
			id: compositionId,
			inputProps,
			port,
			onBrowserDownload: ({chromeMode}) => {
				const browserLabel =
					chromeMode === 'chrome-for-testing'
						? 'Chrome'
						: 'Headless';

				return {
					version: null,
					onProgress: (progress) => {
						const percent = progress.percent ?? 0;
						const total = progress.totalSizeInBytes;
						const downloaded = progress.downloadedBytes;
						const sizeLabel =
							typeof total === 'number' && total > 0
								? `${(downloaded / 1024 / 1024).toFixed(1)}/${(total / 1024 / 1024).toFixed(1)} MB`
								: `${(downloaded / 1024 / 1024).toFixed(1)} MB`;
						logPhase(
							`Get ${browserLabel}`,
							percent,
							sizeLabel,
							percent >= 1,
						);
					},
				};
			},
		});
		finalizeProgressLine();

		console.log(`Rendering composition "${composition.id}" to ${outputLocation}`);
		console.log(
			JSON.stringify(
				{
					title,
					subtitle,
					duration: timeline.duration,
					renderDurationInSeconds: maxSeconds ?? timeline.duration,
					layout,
					port,
					concurrency: concurrency ?? 'default',
					gl: glRenderer ?? 'default',
					videoPlanPath: resolvedVideoPlan.videoPlanPath,
					videoPlanSource: resolvedVideoPlan.videoPlanSource,
					keepBundle,
					keepStagedAudio,
					audioPath,
					stagedAudioPath: stagedAudio.stagedPath,
					outputLocation,
				},
				null,
				2,
			),
		);

		await renderMedia({
			codec: 'h264',
			composition,
			serveUrl: bundled,
			outputLocation,
			inputProps,
			concurrency,
			port,
			onStart: ({frameCount, parallelEncoding, resolvedConcurrency}) => {
				console.log(
					JSON.stringify(
						{
							frameCount,
							parallelEncoding,
							resolvedConcurrency,
							hardwareAcceleration:
								'disabled in this script; this Remotion version only supports hardwareAcceleration for H.264/H.265/ProRes on macOS',
						},
						null,
						2,
					),
				);
			},
			onProgress: ({
				encodedFrames,
				progress,
				renderEstimatedTime,
				renderedFrames,
				stitchStage,
			}) => {
				const phase = stitchStage === 'muxing' ? 'Muxing' : 'Encoding';
				const totalFrames = composition.durationInFrames;
				const details = `phase=${phase} rendered=${renderedFrames}/${totalFrames} encoded=${encodedFrames}/${totalFrames} eta=${formatMilliseconds(renderEstimatedTime)}`;
				logPhase('Rendering', progress, details, progress >= 1);
			},
			chromiumOptions: {
				enableMultiProcessOnLinux: true,
				gl: glRenderer,
			},
		});
		finalizeProgressLine();

		console.log(`Rendered ${outputLocation}`);
	} finally {
		finalizeProgressLine();

		if (!keepBundle && bundled && isTemporaryBundlePath(bundled)) {
			if (removePathIfExists(bundled)) {
				console.log(`Removed temporary Remotion bundle: ${bundled}`);
			}
		}

		if (
			!keepStagedAudio &&
			isInsideDirectory(stagedAudio.stagedPath, publicInputDir)
		) {
			if (removePathIfExists(stagedAudio.stagedPath)) {
				console.log(`Removed staged audio: ${stagedAudio.stagedPath}`);
			}
		}
	}
};

main().catch((error) => {
	console.error(error);
	process.exit(1);
});
