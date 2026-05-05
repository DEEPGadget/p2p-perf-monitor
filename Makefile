# p2p-perf-monitor — 운영 단축 명령
# 정본 사양 → docs/implementation-plan.md §Phase 4

SHELL := /bin/bash
COMPOSE := docker compose
SERVICE := p2p-monitor

.PHONY: help install build up down restart logs ps demo health uninstall

help: ## 명령 목록
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/{printf "  \033[1;36m%-12s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)

install: ## 1회 setup (sudo 필요) — SSH 키, /etc/p2p-monitor, systemd, build, enable
	sudo bash scripts/install.sh

build: ## 이미지 재빌드 (캐시 사용)
	$(COMPOSE) build

up: ## foreground 기동 (개발용; 운영은 systemctl start $(SERVICE))
	$(COMPOSE) up

down: ## 컨테이너 종료
	$(COMPOSE) down

restart: ## 재기동 (systemd 사용)
	sudo systemctl restart $(SERVICE)

logs: ## journald 로그 follow
	journalctl -u $(SERVICE) -f --no-pager

ps: ## 컨테이너 상태
	$(COMPOSE) ps

demo: ## mock 모드로 컨테이너 띄움 (NIC 부재 환경 시연용)
	MEASUREMENT_TOOL=mock $(COMPOSE) up

health: ## /api/health 폴링
	bash scripts/health-check.sh

uninstall: ## 제거 (/etc/p2p-monitor 보존)
	sudo bash scripts/uninstall.sh
