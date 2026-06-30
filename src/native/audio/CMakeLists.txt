nanobind_add_module(
	_native_audio
	NB_STATIC
	STABLE_ABI
	bindings.cpp
	wasapiCapture.cpp
)

target_link_libraries(_native_audio PRIVATE
	ole32
	uuid
	mmdevapi
)

install(TARGETS _native_audio LIBRARY DESTINATION src/_native)
