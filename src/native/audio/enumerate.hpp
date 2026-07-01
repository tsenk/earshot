#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct ProcessAudioInfo {
	uint32_t pid;
	std::string executableName;
};

std::vector<ProcessAudioInfo> listProcessesPlayingAudio();
