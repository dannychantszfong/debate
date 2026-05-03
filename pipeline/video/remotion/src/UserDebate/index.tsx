import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import rawTimeline from './data/sample-timeline.json';
import {
	DebateTimeline,
	DebateVideo,
	UserDebateProps,
	userDebateSchema,
} from './DebateVideo';

const FPS = 30;
const sampleTimeline = rawTimeline as DebateTimeline;

const calculateMetadata: CalculateMetadataFunction<UserDebateProps> = async ({
	props,
}) => {
	const renderDuration = Math.min(
		props.renderDurationInSeconds ?? props.timeline.duration,
		props.timeline.duration,
	);

	return {
		durationInFrames: Math.max(1, Math.ceil(renderDuration * FPS)),
		defaultOutName:
			props.outputName ??
			(props.layout ? `user-debate-${props.layout}` : 'user-debate-render'),
	};
};

export const UserDebateComp: React.FC = () => {
	return (
		<Composition
			id="user-debate-video"
			component={DebateVideo}
			width={1920}
			height={1080}
			fps={FPS}
			schema={userDebateSchema}
			defaultProps={{
				title: '身体自主权与胎儿生命权',
				subtitle: '主持 / 正方 / 反方 · Transcript-driven debate render',
				audioFile: 'user-debate/input/audio.wav',
				layout: 'dual',
				outputName: 'user-debate-preview',
				timeline: sampleTimeline,
			}}
			calculateMetadata={calculateMetadata}
		/>
	);
};
