FROM ubuntu:xenial as compiler

ARG GST_VERSION=1.15.2

RUN sudo apt-get -y update

RUN sudo apt-get install \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-doc \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    gstreamer1.0-nice \
    libglib2.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    libsoup2.4-dev \
    libjson-glib-dev
