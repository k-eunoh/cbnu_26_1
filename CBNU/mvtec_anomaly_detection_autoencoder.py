import os
import glob
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt

import torch.nn as nn
import torch.optim as optim

from PIL import Image
from sklearn.metrics import roc_auc_score, precision_recall_curve
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms


class MVTecDataset(Dataset):
    "MVTec AD 데이터셋 로더"
    def __init__(self, root_dir, category, is_train=True, transform=None):
        self.transform = transform
        self.image_paths = []
        self.labels = []  # 0: Normal, 1: Anomaly

        if is_train:
            img_dir = os.path.join(root_dir, category, "train", "good")
            paths = glob.glob(os.path.join(img_dir, "*.png"))
            self.image_paths.extend(paths)
            self.labels.extend([0] * len(paths))
        else:
            test_dir = os.path.join(root_dir, category, "test")
            for defect_type in os.listdir(test_dir):
                defect_dir = os.path.join(test_dir, defect_type)
                paths = glob.glob(os.path.join(defect_dir, "*.png"))
                self.image_paths.extend(paths)
                label = 0 if defect_type == "good" else 1
                self.labels.extend([label] * len(paths))

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert("RGB")
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label, img_path


class ConvAutoencoder(nn.Module):
    "개선된 CNN 오토인코더"
    def __init__(self):
        super(ConvAutoencoder, self).__init__()

        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),

            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),

            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU()
        )

        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),

            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),

            nn.ConvTranspose2d(32, 3, 3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x


def get_anomaly_score(error_map):
    "오차맵 기반 anomaly score 계산"
    error_map = cv2.GaussianBlur(error_map, (15, 15), 0)

    flat = error_map.flatten()
    k = max(1, int(len(flat) * 0.01))  # 상위 1%
    score = np.mean(np.partition(flat, -k)[-k:])

    return score, error_map


def train_model(model, train_loader, device, num_epochs=120, lr=5e-4):
    mse_loss = nn.MSELoss()
    l1_loss = nn.L1Loss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print("모델 학습 시작...")
    model.train()

    for epoch in range(num_epochs):
        epoch_loss = 0.0

        for images, _, _ in train_loader:
            images = images.to(device)

            outputs = model(images)
            loss = 0.5 * mse_loss(outputs, images) + 0.5 * l1_loss(outputs, images)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(train_loader)
        print(f"Epoch [{epoch+1:03d}/{num_epochs}] Loss: {avg_loss:.6f}")


def evaluate_performance(model, test_loader, device):
    model.eval()
    y_true = []
    y_scores = []

    print("전체 테스트 데이터셋 정량 평가를 진행합니다...")

    with torch.no_grad():
        for images, labels, _ in test_loader:
            images = images.to(device)
            outputs = model(images)

            error = torch.mean((images - outputs) ** 2, dim=1)
            error_map = error.squeeze().cpu().numpy()

            anomaly_score, _ = get_anomaly_score(error_map)

            y_scores.append(anomaly_score)
            y_true.append(labels.item())

    auroc = roc_auc_score(y_true, y_scores)

    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
    f1_scores = (2 * precisions[:-1] * recalls[:-1]) / (
        precisions[:-1] + recalls[:-1] + 1e-8
    )

    best_idx = np.argmax(f1_scores)
    best_f1 = f1_scores[best_idx]
    best_threshold = thresholds[best_idx]

    print("-" * 40)
    print("[전체 평가 결과]")
    print(f"AUROC Score          : {auroc:.4f}")
    print(f"Best F1-Score        : {best_f1:.4f}")
    print(f"Optimal Threshold    : {best_threshold:.4f}")
    print("-" * 40)

    return best_threshold


def visualize_anomaly(model, test_loader, device, threshold, num_samples=3):
    model.eval()
    samples_shown = 0

    print(f"\n최적 임계값({threshold:.4f})을 적용하여 시각화를 시작합니다.")

    with torch.no_grad():
        for images, labels, img_paths in test_loader:
            if labels.item() == 0:
                continue

            images = images.to(device)
            outputs = model(images)

            error = torch.mean((images - outputs) ** 2, dim=1)
            error_map = error.squeeze().cpu().numpy()

            anomaly_score, error_map = get_anomaly_score(error_map)

            prediction = "NG (Defect)" if anomaly_score >= threshold else "OK (Normal)"

            error_map_norm = cv2.normalize(
                error_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
            )
            heatmap = cv2.applyColorMap(error_map_norm, cv2.COLORMAP_JET)

            img_np = images.squeeze().cpu().permute(1, 2, 0).numpy()
            out_np = outputs.squeeze().cpu().permute(1, 2, 0).numpy()

            heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
            overlay = cv2.addWeighted(
                (img_np * 255).astype(np.uint8), 0.5, heatmap_rgb, 0.5, 0
            )

            fig, axes = plt.subplots(1, 4, figsize=(16, 4))

            axes[0].imshow(img_np)
            axes[0].set_title(f"Original\nScore: {anomaly_score:.4f} -> {prediction}")

            axes[1].imshow(out_np)
            axes[1].set_title("Reconstructed")

            axes[2].imshow(error_map, cmap="hot")
            axes[2].set_title("Error Map")

            axes[3].imshow(overlay)
            axes[3].set_title("Overlay Heatmap")

            for ax in axes:
                ax.axis("off")

            plt.suptitle(os.path.basename(img_paths[0]), fontsize=12)
            plt.tight_layout()
            plt.show()

            samples_shown += 1
            if samples_shown >= num_samples:
                break


if __name__ == "__main__":
    print("### train + eval 통합 코드 실행 ###")

    ROOT_DIR = "./mvtec_ad"
    CATEGORY = "bottle"

    BATCH_SIZE = 16
    NUM_EPOCHS = 120
    LEARNING_RATE = 5e-4
    MODEL_PATH = "autoencoder_model_final.pth"

    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05),
        transforms.ToTensor(),
    ])

    test_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])

    train_dataset = MVTecDataset(
        root_dir=ROOT_DIR,
        category=CATEGORY,
        is_train=True,
        transform=train_transform
    )
    test_dataset = MVTecDataset(
        root_dir=ROOT_DIR,
        category=CATEGORY,
        is_train=False,
        transform=test_transform
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("device:", device)
    print("current file:", __file__)
    print("model path:", os.path.abspath(MODEL_PATH))
    print(f"train dataset size: {len(train_dataset)}")
    print(f"test dataset size : {len(test_dataset)}")

    model = ConvAutoencoder().to(device)

    # 1. 학습
    train_model(
        model=model,
        train_loader=train_loader,
        device=device,
        num_epochs=NUM_EPOCHS,
        lr=LEARNING_RATE
    )

    # 2. 저장
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"모델 저장 완료: {MODEL_PATH}")

    # 3. 평가
    optimal_thresh = evaluate_performance(model, test_loader, device)

    # 4. 시각화
    visualize_anomaly(model, test_loader, device, optimal_thresh, num_samples=3)
