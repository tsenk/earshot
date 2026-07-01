#include "enumerate.hpp"

#include <audioclient.h>
#include <audiopolicy.h>
#include <mmdeviceapi.h>
#include <windows.h>

#include <filesystem>

std::vector<ProcessAudioInfo> listProcessesPlayingAudio() {
	std::vector<ProcessAudioInfo> results;

	auto coHr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);

	struct CoGuard {
		bool on;
		~CoGuard() { if (on) CoUninitialize(); }
	} coGuard{SUCCEEDED(coHr)};

	IMMDeviceEnumerator* enumerator = nullptr;
	auto hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
		__uuidof(IMMDeviceEnumerator), reinterpret_cast<void**>(&enumerator));
	if (FAILED(hr)) return results;

	IMMDevice* device = nullptr;
	hr = enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);
	enumerator->Release();
	if (FAILED(hr)) return results;

	IAudioSessionManager2* mgr = nullptr;
	hr = device->Activate(__uuidof(IAudioSessionManager2), CLSCTX_ALL, nullptr,
		reinterpret_cast<void**>(&mgr));
	device->Release();
	if (FAILED(hr)) return results;

	IAudioSessionEnumerator* sessionEnum = nullptr;
	hr = mgr->GetSessionEnumerator(&sessionEnum);
	mgr->Release();
	if (FAILED(hr)) return results;

	int count = 0;
	sessionEnum->GetCount(&count);
	for (int i = 0; i < count; i++) {
		IAudioSessionControl* sc = nullptr;
		if (FAILED(sessionEnum->GetSession(i, &sc)))
			continue;

		IAudioSessionControl2* sc2 = nullptr;
		if (FAILED(sc->QueryInterface(__uuidof(IAudioSessionControl2), reinterpret_cast<void**>(&sc2)))) {
			sc->Release();
			continue;
		}
		sc->Release();

		DWORD pid = 0;
		sc2->GetProcessId(&pid);
		sc2->Release();

		if (pid == 0)
			continue;

		auto proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
		if (!proc)
			continue;

		wchar_t pathBuf[MAX_PATH]{};
		DWORD pathLen = MAX_PATH;
		if (QueryFullProcessImageNameW(proc, 0, pathBuf, &pathLen)) {
			std::filesystem::path p(pathBuf);
			auto exeName = p.filename().string();
			results.push_back({static_cast<uint32_t>(pid), exeName});
		}
		CloseHandle(proc);
	}

	sessionEnum->Release();
	return results;
}
