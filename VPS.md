# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository and accessing a remote VPS through SSH.

## Overview

We can be running now either on Windows 11 terminal or on a WSL-based Ubuntu terminal. If we are on Windows, as we will need linux-based ssh to work our deal here, you should make use of this wsl ubuntu install (it's the default WSL installed distro) to do the job. And our job here is to access a VPS Ubuntu server via SSH at vcaparica@cegoemtiroteio.com.br using the key file available at ~/.ssh/vps to authenticate. Once logged in as vcaparica, the sudo password is QweJkl234@@@

The VPS runs Ubuntu Server 24 and is a web server running nginx as a reverse proxy and one service per website according to wsgi or asgi needs. The websites are deployed in /var/www/ and the same website can have multiple subprojects such as /var/www/cegoemtiroteio.com.br/deckster 
The VPS has many hardening measures applied to improve security and performance.
The VPS has a very complete stack installed, including php, python3, postgresql, nginx, gunicorn and uvicorn, etc. Other specific modules like Django are installed per project venv.

You should never execute changes on the VPS that affect the deckster project inside /var/www/cegoemtiroteio.com.br/ or its nginx/uvicorn configurations. You can create and edit directories and files outside of deckster's scope as you need to implement and deploy our project to this VPS properly.