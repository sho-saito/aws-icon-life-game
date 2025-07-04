# AWS Icon Life

![AWS Icon Life Game Demo](aws-icon-life-game.gif)

AWSのアイコンたちが生命体のように画面上を動き回り、相互作用するシミュレーションゲーム。コンウェイのライフゲームにインスパイアされつつ、AWSサービスアイコンが独自の「生態系」を形成します。

## 概要

このゲームでは、AWSサービスのアイコンが画面上を動き回り、他のアイコンと相互作用します。EC2はVPCの中でないと生存できないなど、実際のAWSサービスの依存関係がゲームメカニクスとして表現されています。

## インストールと実行方法 (macOS)

1. リポジトリをクローン
```
git clone https://github.com/sho-saito/aws-icon-life-game.git
cd aws-icon-life-game
```

2. Python仮想環境の作成と有効化
```
python3 -m venv venv
source venv/bin/activate
```

3. 依存パッケージのインストールと実行
```
pip install -r requirements.txt
python main.py
```

## 操作方法

- **マウス左クリック (空白部分)**: クリックした位置に新しいランダムなアイコンを配置
- **マウス左クリック (アイコン上)**: アイコンを選択
- **マウス左クリック+ドラッグ**: アイコンを移動
- **スペースキー**: ランダムな位置に新しいアイコンを配置
- **ESCキー**: ゲーム終了

## ゲームの特徴

- **依存関係**: EC2はVPCの中でないと体力が減少するなど、実際のAWSサービスの依存関係を表現
- **補完関係**: EC2とEBSなど、相互に補完し合うサービスの関係を表現
- **アイコン固有の動き**: 各AWSサービスの特性に合わせた独自の動きパターン
- **進行システム**: 依存関係や補完関係の達成状況を追跡し、通知を表示

## サポートされているAWSサービス

- EC2, S3, VPC, Lambda, EBS, RDS, IAM, DynamoDB, API Gateway, CloudFront

## 開発について

このプロジェクトは、Amazon Q Developer CLIを使用して開発されました。コードの作成やドキュメント作成など、プロジェクト全体の開発プロセスにAmazon Q Developer CLIが活用されています。
