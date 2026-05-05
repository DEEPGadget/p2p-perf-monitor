# NIC 환경

## 하드웨어

| 항목 | 값 |
|------|-----|
| NIC 모델 | NVIDIA Mellanox **ConnectX-6** (MT28908, PCI ID `15B3:101B`) |
| 포트 속도 | **200 Gb/s** per port (HDR, RoCE v2) |
| 포트 수 | **2-port NIC** — 서버당 1장. **P2P 데모는 1-port만 사용** |
| 사용 포트 | 양쪽 서버 모두 **동일 포트** (통상 `mlx5_0`, 라이브 검증 필요) |
| 폼팩터 | PCIe Gen5 x16 |
| 케이블 | DAC / AOC (200G QSFP56) — 결정 후 추가 기재 |
| 토폴로지 | 직결 가정 (단순 P2P) |

### 2-port NIC인데 1-port만 쓰는 이유

PCIe Gen5 x16 단방향 실효 BW ≈ 256 Gb/s. 두 포트 동시 200G 단방향(합산 400G)은 PCIe 병목으로 ~200~240 Gb/s에서 막힘. 1-port + BIDIR(`-b`)이 합산 ~380 Gb/s로 시각 임팩트가 더 큼. 미사용 포트는 UI 다이어그램에 표시하지 않음 (가독성 우선).

## 호스트 환경

| 항목 | Server A | Server B |
|------|---------|---------|
| 모델 | **dg5W-H200NVL-4** (Tower 5U) | **dg5R-PRO6000SE-8** (랙마운트 6U) |
| 가속기 | NVIDIA H200 NVL × 4 | RTX PRO 6000 Server Edition × 10 |
| OS | Ubuntu 22.04 LTS (or 24.04) | 동일 |
| Kernel | 5.15+ (RoCE v2 안정 동작) | 동일 |
| **냉각** | **Liquid-Cooled** (NIC IC + 광 트랜시버 모두) | 동일 |

서버 모델별 상세 스펙(폼팩터·CPU·RAM·전원)은 `~/workspace/projects/inspection-system/context/target-servers.md` 참조.
본 데모는 위 두 모델의 RoCE P2P 성능을 보여주는 용도. 부스 환경에서는 dg5W·dg5R 한 쌍 + 액냉 시스템 일체가 시연됨.

## 드라이버·라이브러리

| 항목 | 버전 가정 | 비고 |
|------|----------|------|
| MLNX_OFED | 24.10 LTS 또는 최신 | `mlnxofedinstall --upstream-libs --dpdk` 권장 옵션 검토 |
| `rdma-core` | OFED 동봉 | 시스템 패키지가 아닌 OFED 패키지 사용 |
| `perftest` | OFED 동봉 (`/usr/bin/ib_write_bw` 등) | 별도 빌드 불필요 |
| `iperf3` | apt 패키지 또는 OFED 동봉 | TCP 비교용 |

설치 절차는 운영 문서(`README.md`)에 기재. 본 파일은 환경 가정 기록.

## 네트워크 설정

이중 네트워크 — **관리망**(SSH 제어) + **RDMA 망**(측정 트래픽) 분리.

| 항목 | 값 |
|------|-----|
| RoCE 버전 | **v2** (UDP 캡슐화). GID 3 라이브 검증 완료 |
| GID index | **3** (RoCE v2 IPv4) — `show_gids` 로 확정 |
| MTU | **9000 (Jumbo) 권장** — 라이브 첫 측정 시 1024 (Jumbo 미적용)로 ~181 Gb/s. 9000 적용 후 195+ 예상 |
| PFC / ECN | RoCE 무손실 지원 시 활성. 직결이면 보통 불필요 |
| 관리망 (SSH) | `192.168.1.0/24`. SSH IP: dg5W=`192.168.1.166`, dg5R=`192.168.1.204` |
| RDMA 망 | `25.47.1.0/24`. RDMA IP: dg5W=`25.47.1.10`, dg5R=`25.47.1.11` |

이전 IB 모드 (`ibp2s0f0`/`ibs7f0`)에서 다음 절차로 RoCE 전환 완료:
1. ConnectX-6 link layer를 Ethernet으로 전환 (`mlxconfig -d <dev> set LINK_TYPE_P1=2`)
2. RoCE v2 활성화, IP 재할당 (25.47.1.x)
3. 인터페이스명 `ib*` → `enp*`/`ens*` 변경됨

## NIC 디바이스 명명

2-port ConnectX-6 환경 기준:
- 디바이스: `mlx5_0` (포트 1) / `mlx5_1` (포트 2). 2-port NIC라 두 디바이스 모두 노출
- **사용 포트는 1개**, 양쪽 서버 동일 포트 (통상 `mlx5_0`)
- 인터페이스명 (라이브 검증 완료):
  | 서버 | netdev 인터페이스 | RDMA IP | RDMA device | 비고 |
  |------|-----------------|---------|------------|------|
  | dg5W | `enp2s0f0np0` | `25.47.1.10` | `mlx5_0` | 전통 명명 (PCIe 02:00.0) |
  | dg5R | `ens7f0np0` | `25.47.1.11` | `rocep100s0f0` | udev `roce p<bus_dec> s<slot> f<func>` (PCIe 64:00.0 = bus 100 dec) |
- driver는 양쪽 모두 `mlx5_core` (perftest·ibv 동일하게 동작)
- 환경변수: `NIC_DEVICE_A=mlx5_0`, `NIC_DEVICE_B=rocep100s0f0`
- netdev ↔ RDMA device 매핑:
  ```bash
  ls /sys/class/net/<iface>/device/infiniband/   # → mlx5_0 또는 rocep...
  ```
- 트랜시버 `ethtool -m` 직접 호출은 netdev 인터페이스명 사용 (`ethtool -m enp2s0f0np0`)

## 사전 검증 명령

```bash
# RDMA 디바이스 존재 확인
ibstat
ibv_devices

# GID 테이블 확인 (RoCE v2 GID index 결정)
show_gids
# 출력 예: mlx5_0  1  3  fe80::...:0000  10.x.x.10  v2  enp1s0f0np0
#                       ^                              ^
#                       GID index                      RoCE 버전

# Loopback BW (측정 도구 동작 확인)
ib_write_bw -d mlx5_0 -F -D 5 &
ib_write_bw -d mlx5_0 -F -D 5 localhost

# 두 서버 간 직접 측정 (실 환경)
# Server A:
ib_write_bw -d mlx5_0 -F --report_gbits -D 30
# Server B:
ib_write_bw -d mlx5_0 -F --report_gbits -D 30 <server-A-ip>
```

## 200G RoCE 기대·실측 성능

| 측정 | 기대값 | 실측 | 비고 |
|------|--------|------|------|
| `ib_write_bw` (msg=64K, MTU=1024) | — | **181.32 Gb/s** | 2026-05-05 라이브 5초 |
| `ib_write_bw` (msg=64K, MTU=9000) | 195~199 Gb/s | TBD | Jumbo 적용 후 재측정 |
| `ib_write_bw -b` (BIDIR, MTU=9000) | ~380 Gb/s 합산 | TBD | UI Y축 400 max |
| `ib_read_lat` (msg=8B) | 1.5~2.0 µs avg | TBD | RDMA Read RTT |
| `iperf3 -P 8` (TCP) | 150~180 Gb/s | TBD | RDMA 대비 GAP 가시화 |

위 수치는 측정 도구 출력 파싱 검증·테스트 fixture 작성·UI Y축 max 결정의 기준.

## 광 트랜시버

| 항목 | 값 |
|------|-----|
| 모듈 종류 | **QSFP56** (200G optical) — UI 다이어그램 표기와 일치 |
| 냉각 | Liquid-Cooled (회사 자체 솔루션) |
| 온도 측정 | `ethtool -m <netdev>` 의 `Module temperature` 또는 `mlxlink --json` |
| 운영 한계 | ~80°C |

온도 임계값(warning/danger) 정본 → `.claude/rules/measurement.md` §임계값 / 색상 코딩.

## 결정 대기 항목

부스 환경 관련 미결정 항목은 → `handoff/current-state.md` "결정 대기 항목" 섹션에서 통합 관리.

## 갱신 정책

- NIC 모델·드라이버 변경 시 본 파일 갱신
- 갱신 시 `.claude/rules/measurement.md`의 호출 규약과 일관성 유지
- 갱신 주체: 사용자 또는 사용자 지시 받은 에이전트
