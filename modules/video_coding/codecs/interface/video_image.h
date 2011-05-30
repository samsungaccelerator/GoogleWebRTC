/*
 *  Copyright (c) 2011 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef VIDEO_IMAGE_H
#define VIDEO_IMAGE_H

#include "typedefs.h"
#include <stdlib.h>

namespace webrtc
{

enum VideoFrameType
{
    kKeyFrame = 0,
    kDeltaFrame = 1,
    kGoldenFrame = 2,
    kAltRefFrame = 3,
    kSkipFrame = 4
};

class RawImage
{
public:
    RawImage() :    _width(0), _height(0), _timeStamp(0), _buffer(NULL),
                    _length(0), _size(0) {}

    RawImage(WebRtc_UWord8* buffer, WebRtc_UWord32 length,
        WebRtc_UWord32 size) :
                    _width(0), _height(0), _timeStamp(0),
                    _buffer(buffer), _length(length), _size(size) {}

    WebRtc_UWord32    _width;
    WebRtc_UWord32    _height;
    WebRtc_UWord32    _timeStamp;
    WebRtc_UWord8*    _buffer;
    WebRtc_UWord32    _length;
    WebRtc_UWord32    _size;
};

class EncodedImage
{
public:
    EncodedImage() :
                     _encodedWidth(0), _encodedHeight(0), _timeStamp(0),
                     _frameType(kDeltaFrame), _buffer(NULL), _length(0), _size(0),
                     _completeFrame(false) {}

    EncodedImage(WebRtc_UWord8* buffer,
                 WebRtc_UWord32 length,
                 WebRtc_UWord32 size) :
                     _encodedWidth(0), _encodedHeight(0), _timeStamp(0),
                     _frameType(kDeltaFrame), _buffer(buffer), _length(length),
                     _size(size), _completeFrame(false) {}

    WebRtc_UWord32              _encodedWidth;
    WebRtc_UWord32              _encodedHeight;
    WebRtc_UWord32              _timeStamp;
    VideoFrameType             _frameType;
    WebRtc_UWord8*              _buffer;
    WebRtc_UWord32              _length;
    WebRtc_UWord32              _size;
    bool                        _completeFrame;
};

} // namespace webrtc

#endif // VIDEO_IMAGE_H
