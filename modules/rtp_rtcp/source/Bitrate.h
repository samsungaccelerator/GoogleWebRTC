/*
 *  Copyright (c) 2011 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef WEBRTC_MODULES_RTP_RTCP_SOURCE_BITRATE_H_
#define WEBRTC_MODULES_RTP_RTCP_SOURCE_BITRATE_H_

#include "typedefs.h"
#include "rtp_rtcp_config.h"     // misc. defines (e.g. MAX_PACKET_LENGTH)
#include "common_types.h"            // Transport
#include "list_wrapper.h"

namespace webrtc {
class Bitrate
{
public:
    Bitrate();

    // initialize members
    void Init();

    // calculate rates
    void Process();

    // update with a packet
    void Update(const WebRtc_Word32 bytes);

    // packet rate last second, updated roughly every 100 ms
    WebRtc_UWord32 PacketRate() const;

    // bitrate last second, updated roughly every 100 ms
    WebRtc_UWord32 BitrateLast() const;

    // bitrate last second, updated now
    WebRtc_UWord32 BitrateNow() const;

private:
    WebRtc_UWord32            _packetRate;
    WebRtc_UWord32            _bitrate;
    WebRtc_UWord8             _bitrateNextIdx;
    WebRtc_UWord32            _packetRateArray[10];
    WebRtc_UWord32            _bitrateArray[10];
    WebRtc_UWord32            _bitrateDiffMS[10];
    WebRtc_UWord32            _timeLastRateUpdate;
    WebRtc_UWord32            _bytesCount;
    WebRtc_UWord32            _packetCount;
};

struct DataTimeSizeTuple
{
    DataTimeSizeTuple(WebRtc_Word64 sizeBytes, WebRtc_Word64 timeCompleteMs) :
                            _sizeBytes(sizeBytes), _timeCompleteMs(timeCompleteMs) {}

    WebRtc_Word64     _sizeBytes;
    WebRtc_Word64     _timeCompleteMs;
};

class BitRateStats
{
public:
    BitRateStats();
    ~BitRateStats();

    void Init();
    void Update(WebRtc_Word64 packetSizeBytes, WebRtc_Word64 nowMs);
    WebRtc_UWord32 BitRateNow();

private:
    ListWrapper              _dataSamples;
    WebRtc_UWord32        _avgSentBitRateBps;
};
} // namespace webrtc

#endif // WEBRTC_MODULES_RTP_RTCP_SOURCE_BITRATE_H_
